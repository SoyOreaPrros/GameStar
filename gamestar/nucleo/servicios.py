"""Registro y despacho de servicios de negocio.

Cada módulo (rama feature/*) registra sus funciones con el decorador ``@servicio``.
El despachador valida la sesión, aplica el control de acceso por rol (RNF03) y
ejecuta cada servicio dentro de una transacción (RNF02). El mismo despachador se
usa desde el servidor central (red) o en el mismo equipo (modo local).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import secrets
import threading
from dataclasses import dataclass, field
from typing import Callable

from . import db, esquema
from .errores import ErrorGameStar, ErrorPermiso, ErrorSesion, ErrorValidacion

EMPLEADO = "EMPLEADO"
ADMINISTRADOR = "ADMINISTRADOR"
AMBOS = (EMPLEADO, ADMINISTRADOR)


@dataclass
class Servicio:
    nombre: str
    funcion: Callable
    roles: tuple
    escritura: bool
    publico: bool


SERVICIOS: dict[str, Servicio] = {}


def servicio(nombre: str, roles=AMBOS, escritura: bool = False, publico: bool = False):
    """Registra una función de negocio. ``roles`` indica qué perfiles pueden usarla."""

    def decorar(funcion):
        SERVICIOS[nombre] = Servicio(nombre, funcion, tuple(roles), escritura, publico)
        return funcion

    return decorar


def cargar_modulos() -> list[str]:
    """Importa los servicios de cada módulo presente en ``gamestar.modulos``."""
    import gamestar.modulos as paquete

    cargados = []
    for info in sorted(pkgutil.iter_modules(paquete.__path__), key=lambda m: m.name):
        try:
            importlib.import_module(f"gamestar.modulos.{info.name}.servicios")
        except ModuleNotFoundError as e:
            if e.name != f"gamestar.modulos.{info.name}.servicios":
                raise
            continue
        cargados.append(info.name)
    return cargados


@dataclass
class Contexto:
    con: object
    usuario: dict | None
    despachador: "Despachador"
    token: str | None = None
    extras: dict = field(default_factory=dict)

    @property
    def id_usuario(self) -> int:
        return self.usuario["idUsuario"]

    @property
    def id_sucursal(self) -> int:
        return self.usuario["idSucursal"]

    def abrir_sesion(self, id_usuario: int) -> str:
        return self.despachador._abrir_sesion(id_usuario)

    def cerrar_sesion(self) -> None:
        self.despachador._cerrar_sesion(self.token)


class Despachador:
    def __init__(self, ruta_db: str):
        self.ruta_db = ruta_db
        esquema.inicializar(ruta_db)
        cargar_modulos()
        self._sesiones: dict[str, int] = {}
        self._lock = threading.Lock()

    # -- sesiones -----------------------------------------------------------
    def _abrir_sesion(self, id_usuario: int) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sesiones[token] = id_usuario
        return token

    def _cerrar_sesion(self, token: str | None) -> None:
        with self._lock:
            self._sesiones.pop(token or "", None)

    def _usuario_de(self, con, token: str | None) -> dict:
        with self._lock:
            id_usuario = self._sesiones.get(token or "")
        if id_usuario is None:
            raise ErrorSesion("La sesión no está activa. Inicia sesión de nuevo.")
        # Se lee el usuario en cada llamada para que un cambio de rol (CU-12) aplique
        # de inmediato a sus permisos.
        usuario = db.fila(con.execute(
            "SELECT u.idUsuario, u.nombre, u.usuarioAcceso, u.rol, u.idSucursal, s.nombre AS sucursal "
            "FROM usuario u JOIN sucursal s ON s.idSucursal = u.idSucursal WHERE u.idUsuario = ?",
            (id_usuario,)))
        if usuario is None:
            self._cerrar_sesion(token)
            raise ErrorSesion("La sesión no está activa. Inicia sesión de nuevo.")
        return usuario

    # -- ejecución ----------------------------------------------------------
    def ejecutar(self, nombre: str, token: str | None = None, args: dict | None = None):
        srv = SERVICIOS.get(nombre)
        if srv is None:
            raise ErrorGameStar(f"La función '{nombre}' no está disponible en el servidor.")
        args = dict(args or {})
        with db.transaccion(self.ruta_db, srv.escritura) as con:
            usuario = None
            if not srv.publico:
                usuario = self._usuario_de(con, token)
                if usuario["rol"] not in srv.roles:
                    raise ErrorPermiso("Tu rol no tiene permiso para usar esta función.")
            ctx = Contexto(con, usuario, self, token)
            try:
                inspect.signature(srv.funcion).bind(ctx, **args)
            except TypeError:
                raise ErrorValidacion(f"Datos incompletos o no reconocidos para '{nombre}'.") from None
            return srv.funcion(ctx, **args)
