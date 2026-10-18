"""Pruebas de la rama feature/usuarios-acceso (CU-01, CU-10, CU-11, CU-12, RNF03)."""

import unittest

from gamestar.nucleo.errores import ErrorPermiso, ErrorSesion, ErrorValidacion
from tests.base import CasoGameStar


class PruebasUsuarios(CasoGameStar):
    def setUp(self):
        super().setUp()
        self.admin = self.crear_admin()

    def test_admin_inicial_solo_una_vez(self):
        with self.assertRaises(ErrorValidacion):
            self.publico("usuarios.crear_administrador_inicial", nombre="Otro", usuarioAcceso="otro",
                         contrasena="x", idSucursal=1)

    def test_credenciales_invalidas_cu01(self):
        with self.assertRaises(ErrorValidacion) as e:
            self.entrar("dueno", "incorrecta")
        self.assertIn("no son válidas", str(e.exception))
        with self.assertRaises(ErrorValidacion):
            self.entrar("noexiste", "Clave123")

    def test_registrar_y_entrar_cu10(self):
        u = self.admin("usuarios.registrar", nombre="Ana López", usuarioAcceso="ana", contrasena="123",
                       rol="EMPLEADO", idSucursal=2)
        self.assertEqual(u["rol"], "EMPLEADO")
        self.assertEqual(u["sucursal"], "Sucursal 2")
        self.assertNotIn("contrasena", u)
        ana = self.entrar("ana", "123")
        self.assertTrue(ana("usuarios.cerrar_sesion"))
        with self.assertRaises(ErrorSesion):
            ana("usuarios.cerrar_sesion")  # la sesión ya no está activa

    def test_usuario_de_acceso_unico(self):
        self.admin("usuarios.registrar", nombre="Ana", usuarioAcceso="ana", contrasena="1", rol="EMPLEADO", idSucursal=1)
        with self.assertRaises(ErrorValidacion):
            self.admin("usuarios.registrar", nombre="Ana 2", usuarioAcceso="ANA", contrasena="1", rol="EMPLEADO", idSucursal=1)

    def test_rol_invalido_rfbd02(self):
        with self.assertRaises(ErrorValidacion):
            self.admin("usuarios.registrar", nombre="X", usuarioAcceso="x", contrasena="1", rol="GERENTE", idSucursal=1)

    def test_modificar_cu11(self):
        u = self.admin("usuarios.registrar", nombre="Ana", usuarioAcceso="ana", contrasena="1", rol="EMPLEADO", idSucursal=1)
        self.admin("usuarios.modificar", idUsuario=u["idUsuario"], nombre="Ana María", usuarioAcceso="anam",
                   idSucursal=2, contrasena="nueva")
        ana = self.entrar("anam", "nueva")
        self.assertIsNotNone(ana)
        with self.assertRaises(ErrorValidacion):
            self.entrar("anam", "1")

    def test_rbac_rnf03_y_cambio_de_rol_cu12(self):
        u = self.admin("usuarios.registrar", nombre="Ana", usuarioAcceso="ana", contrasena="1", rol="EMPLEADO", idSucursal=1)
        ana = self.entrar("ana", "1")
        with self.assertRaises(ErrorPermiso):
            ana("usuarios.listar")
        self.admin("usuarios.asignar_rol", idUsuario=u["idUsuario"], rol="ADMINISTRADOR")
        self.assertTrue(ana("usuarios.listar"))  # sus permisos cambian de inmediato

    def test_no_queda_sin_administrador(self):
        lista = self.admin("usuarios.listar")
        with self.assertRaises(ErrorValidacion):
            self.admin("usuarios.asignar_rol", idUsuario=lista[0]["idUsuario"], rol="EMPLEADO")

    def test_sin_sesion(self):
        with self.assertRaises(ErrorSesion):
            self.publico("usuarios.listar")


if __name__ == "__main__":
    unittest.main()
