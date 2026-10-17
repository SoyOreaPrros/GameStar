"""Utilidades comunes para las pruebas: base de datos temporal y sesiones por rol."""

from __future__ import annotations

import os
import tempfile
import unittest

from gamestar.nucleo.servicios import Despachador


class Sesion:
    def __init__(self, despachador: Despachador, token: str | None):
        self.d, self.token = despachador, token

    def __call__(self, servicio: str, **args):
        return self.d.ejecutar(servicio, self.token, args)


class CasoGameStar(unittest.TestCase):
    """Base con un despachador sobre una base de datos temporal."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self._dir.name, "prueba.db")
        self.d = Despachador(self.ruta)
        self.publico = Sesion(self.d, None)

    def tearDown(self):
        self._dir.cleanup()

    def crear_admin(self, usuario="dueno", contrasena="Clave123", sucursal=1):
        self.publico("usuarios.crear_administrador_inicial", nombre="Dueño del local", usuarioAcceso=usuario,
                     contrasena=contrasena, idSucursal=sucursal)
        return self.entrar(usuario, contrasena)

    def entrar(self, usuario, contrasena) -> Sesion:
        r = self.publico("usuarios.iniciar_sesion", usuarioAcceso=usuario, contrasena=contrasena)
        return Sesion(self.d, r["token"])
