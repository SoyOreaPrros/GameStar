"""Ventana principal, navegación entre pantallas y encabezado común.

Elementos comunes de la interfaz (2.2.2.A): encabezado con el logotipo, el nombre de
la pantalla, la insignia del rol activo y el enlace "Cerrar sesión".
"""

from __future__ import annotations

import importlib
import pkgutil
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import messagebox

from gamestar import NOMBRE_SISTEMA, SUBTITULO_SISTEMA
from gamestar.nucleo.errores import ErrorConexion, ErrorGameStar, ErrorSesion

from . import tema as t
from . import widgets as w

RECURSOS = Path(__file__).resolve().parent / "recursos"

ROL_EMPLEADO = "EMPLEADO"
ROL_ADMINISTRADOR = "ADMINISTRADOR"
NOMBRE_ROL = {ROL_EMPLEADO: "Empleado", ROL_ADMINISTRADOR: "Administrador"}
ESTILO_ROL = {ROL_EMPLEADO: "negro", ROL_ADMINISTRADOR: "rojo"}

# Tipos de función del menú y su código de colores (leyenda del prototipo final).
COMPARTIDA, DEL_EMPLEADO, SOLO_ADMIN = "compartida", "empleado", "admin"
TIPO_FUNCION = {
    COMPARTIDA: ("Función compartida", "plata"),
    DEL_EMPLEADO: ("Función del empleado", "negro"),
    SOLO_ADMIN: ("Solo administrador", "rojo"),
}


@dataclass
class TarjetaMenu:
    pantalla: str
    titulo: str
    descripcion: str
    icono: str
    roles: tuple
    tipo: str
    orden: dict = field(default_factory=dict)  # {rol: posición}
    indicador: object = None  # función(app) -> texto de aviso opcional


class Pantalla(tk.Frame):
    """Base de todas las pantallas internas."""

    titulo = ""
    pastilla = None            # (texto, estilo) junto al título
    volver = "menu"            # pantalla a la que regresa "‹ Menú principal"
    texto_volver = "Menú principal"
    con_encabezado = True
    roles = (ROL_EMPLEADO, ROL_ADMINISTRADOR)

    def __init__(self, padre, app: "App", **kw):
        super().__init__(padre, bg=t.FONDO)
        self.app = app
        self.construir(**kw)

    def construir(self, **kw):
        pass

    def llamar(self, servicio, **args):
        return self.app.llamar(servicio, **args)


class App(tk.Tk):
    def __init__(self, conexion, cfg=None, cargar_modulos=True):
        super().__init__()
        from gamestar import config
        self.cfg = cfg or config.cargar()
        self.conexion = conexion
        self.usuario: dict | None = None
        self.estado: dict = {}
        self.pantallas: dict[str, type] = {}
        self.tarjetas: list[TarjetaMenu] = []
        self.actual: Pantalla | None = None
        self.ultimo_error: str | None = None

        self.title(f"{NOMBRE_SISTEMA} · {SUBTITULO_SISTEMA}")
        self.configure(bg=t.FONDO)
        self.geometry("1389x868")
        self.minsize(1180, 720)
        try:
            self._icono = tk.PhotoImage(file=RECURSOS / "icono.png")
            self.iconphoto(True, self._icono)
        except tk.TclError:
            pass
        self.logo_encabezado = tk.PhotoImage(file=RECURSOS / "logo_encabezado.png")
        self.logo_login = tk.PhotoImage(file=RECURSOS / "logo_login.png")
        w.configurar_estilos(self)
        w.instalar_rueda(self)

        tk.Frame(self, bg=t.ROJO, height=3).pack(fill="x", side="top")  # franja de la barra de título
        self.encabezado = tk.Frame(self, bg=t.BLANCO)
        self.linea_encabezado = tk.Frame(self, bg=t.BORDE, height=1)
        self.contenedor = tk.Frame(self, bg=t.FONDO)
        self.contenedor.pack(fill="both", expand=True)

        from .menu import MenuPrincipal
        self.registrar_pantalla("menu", MenuPrincipal)
        if cargar_modulos:
            self.cargar_modulos()
        self.mostrar("login" if "login" in self.pantallas else "sin_modulos")

    # -- registro de módulos ------------------------------------------------
    def cargar_modulos(self):
        import gamestar.modulos as paquete
        for info in sorted(pkgutil.iter_modules(paquete.__path__), key=lambda m: m.name):
            try:
                mod = importlib.import_module(f"gamestar.modulos.{info.name}.pantallas")
            except ModuleNotFoundError as e:
                if e.name != f"gamestar.modulos.{info.name}.pantallas":
                    raise
                continue
            mod.registrar(self)

    def registrar_pantalla(self, clave: str, clase: type):
        self.pantallas[clave] = clase

    def registrar_tarjeta(self, tarjeta: TarjetaMenu):
        self.tarjetas.append(tarjeta)

    # -- navegación ---------------------------------------------------------
    def mostrar(self, clave: str, **kw):
        if clave == "sin_modulos":
            return self._sin_modulos()
        clase = self.pantallas.get(clave)
        if clase is None:
            messagebox.showinfo(NOMBRE_SISTEMA, "Esta función todavía no está integrada.")
            return
        if clase.con_encabezado and (self.usuario is None or self.usuario["rol"] not in clase.roles):
            return  # RNF03: solo se muestran funciones permitidas para el rol
        if self.actual is not None:
            self.actual.destroy()
        for hijo in self.encabezado.winfo_children():
            hijo.destroy()
        self.actual = clase(self.contenedor, self, **kw)
        if clase.con_encabezado:
            self._construir_encabezado(self.actual)
            self.encabezado.pack(fill="x", before=self.contenedor)
            self.linea_encabezado.pack(fill="x", before=self.contenedor)
        else:
            self.encabezado.pack_forget()
            self.linea_encabezado.pack_forget()
        self.actual.pack(fill="both", expand=True)

    def _construir_encabezado(self, p: Pantalla):
        e = self.encabezado
        izq = tk.Frame(e, bg=t.BLANCO)
        izq.pack(side="left", padx=(34, 0), pady=12)
        tk.Label(izq, image=self.logo_encabezado, bg=t.BLANCO, bd=0).pack(side="left")
        tk.Frame(izq, bg=t.BORDE, width=1, height=34).pack(side="left", padx=(22, 22))
        if p.volver:
            atras = tk.Frame(izq, bg=t.BLANCO, cursor="hand2")
            atras.pack(side="left", padx=(0, 20))
            ic = w.icono(atras, "atras", tam=18)
            ic.pack(side="left", padx=(0, 6))
            lbl = w.enlace(atras, p.texto_volver, lambda: self.mostrar(p.volver), estilo="enlace_normal", bg=t.BLANCO)
            lbl.pack(side="left")
            ic.bind("<Button-1>", lambda ev: self.mostrar(p.volver))
        titulo = p.titulo() if callable(p.titulo) else p.titulo
        w.etiqueta(izq, titulo, "titulo", bg=t.BLANCO).pack(side="left")
        if p.pastilla:
            w.Pastilla(izq, *p.pastilla).pack(side="left", padx=(22, 0))
        der = tk.Frame(e, bg=t.BLANCO)
        der.pack(side="right", padx=(0, 34))
        if self.usuario:
            w.Pastilla(der, NOMBRE_ROL[self.usuario["rol"]], ESTILO_ROL[self.usuario["rol"]], alto=32).pack(side="left", padx=(0, 22))
        w.enlace(der, "Cerrar sesión", self.cerrar_sesion, estilo="enlace_normal", bg=t.BLANCO).pack(side="left")

    def _sin_modulos(self):
        marco = tk.Frame(self.contenedor, bg=t.FONDO)
        marco.pack(expand=True)
        tk.Label(marco, image=self.logo_login, bg=t.FONDO).pack(pady=(0, 16))
        w.etiqueta(marco, "No hay módulos integrados todavía.", "seccion").pack()
        w.etiqueta(marco, "Integra la rama feature/usuarios-acceso para habilitar el inicio de sesión.", "tenue").pack()
        self.actual = marco

    # -- sesión -------------------------------------------------------------
    def iniciar_sesion(self, sesion: dict):
        self.conexion.token = sesion["token"]
        self.usuario = sesion["usuario"]
        self.estado = {}
        self.mostrar("menu")

    def cerrar_sesion(self, avisar_servidor=True):
        if avisar_servidor and self.conexion.token:
            try:
                self.conexion.llamar("usuarios.cerrar_sesion")
            except ErrorGameStar:
                pass
        self.conexion.token = None
        self.usuario = None
        self.estado = {}
        self.mostrar("login")

    # -- servicios ----------------------------------------------------------
    def llamar(self, servicio: str, **args):
        """Invoca un servicio. Si falla, informa al usuario y regresa ``None``."""
        self.ultimo_error = None
        try:
            self.configure(cursor="watch")
            self.update_idletasks()
            return self.conexion.llamar(servicio, **args)
        except ErrorGameStar as e:
            self.ultimo_error = e.tipo
            self._informar(e)
        finally:
            try:
                self.configure(cursor="")
            except tk.TclError:
                pass
        return None

    def _informar(self, e: ErrorGameStar):
        if isinstance(e, ErrorSesion):
            messagebox.showwarning(NOMBRE_SISTEMA, e.mensaje, parent=self)
            self.cerrar_sesion(avisar_servidor=False)
        elif isinstance(e, ErrorConexion):
            messagebox.showerror("Sin conexión", e.mensaje, parent=self)
        else:
            messagebox.showwarning(NOMBRE_SISTEMA, e.mensaje, parent=self)

    def aviso(self, mensaje, titulo=NOMBRE_SISTEMA):
        messagebox.showinfo(titulo, mensaje, parent=self)

    def confirmar(self, mensaje, titulo=NOMBRE_SISTEMA) -> bool:
        return messagebox.askyesno(titulo, mensaje, parent=self)


class Dialogo(tk.Toplevel):
    """Ventana modal para formularios breves (modificar, asignar rol, etc.)."""

    def __init__(self, app: App, titulo: str, ancho=480):
        super().__init__(app)
        self.app = app
        self.title(titulo)
        self.configure(bg=t.FONDO)
        self.transient(app)
        self.resizable(False, False)
        self.resultado = None
        self.tarjeta = w.Tarjeta(self, pad=26)
        self.tarjeta.configure(width=ancho)
        self.tarjeta.pack(fill="both", expand=True, padx=18, pady=18)
        self.cuerpo = self.tarjeta.cuerpo
        w.etiqueta(self.cuerpo, titulo, "seccion", bg=t.BLANCO).pack(anchor="w", pady=(0, 16))
        self.bind("<Escape>", lambda e: self.destroy())

    def botones(self, texto_aceptar, al_aceptar):
        fila = tk.Frame(self.cuerpo, bg=t.BLANCO)
        fila.pack(fill="x", pady=(10, 0))
        w.Boton(fila, texto_aceptar, al_aceptar).pack(side="right")
        w.Boton(fila, "Cancelar", self.destroy, estilo="secundario").pack(side="right", padx=(0, 12))

    def mostrar(self):
        self.update_idletasks()
        x = self.app.winfo_rootx() + (self.app.winfo_width() - self.winfo_reqwidth()) // 2
        y = self.app.winfo_rooty() + (self.app.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        self.wait_window()
        return self.resultado
