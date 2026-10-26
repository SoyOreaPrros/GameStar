"""Pruebas de la rama feature/reportes-bitacora (CU-15, RFBD09, RNF04)."""

import unittest

from gamestar.modulos.reportes_bitacora.bitacora import registrar as bitacora
from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorPermiso, ErrorValidacion
from tests.base import CasoGameStar


class PruebasReportes(CasoGameStar):
    def setUp(self):
        super().setUp()
        self.admin = self.crear_admin()

    def test_reporte_vacio_con_aviso_y_trazabilidad(self):
        for tipo in ("INVENTARIO", "VENTAS", "REPARACIONES"):
            r = self.admin("reportes.generar", tipo=tipo)
            self.assertEqual(r["tipo"], tipo)
            self.assertEqual(r["filas"], [])
            self.assertTrue(r["aviso"])  # flujo alterno 3.1 del CU-15
            self.assertEqual(r["solicitadoPor"], "Dueño del local")
        con = db.conectar(self.ruta)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM reporte WHERE idUsuario = 1").fetchone()[0], 3)  # RFBD09
        con.close()

    def test_tipo_invalido(self):
        with self.assertRaises(ErrorValidacion):
            self.admin("reportes.generar", tipo="GANANCIAS")

    def test_solo_administrador(self):
        self.admin("usuarios.registrar", nombre="E", usuarioAcceso="e", contrasena="1", rol="EMPLEADO", idSucursal=1)
        emp = self.entrar("e", "1")
        with self.assertRaises(ErrorPermiso):
            emp("reportes.generar", tipo="VENTAS")
        with self.assertRaises(ErrorPermiso):
            emp("reportes.mas_vendidos")

    def test_bitacora_registra_usuario_y_fecha(self):
        con = db.conectar(self.ruta)
        bitacora(con, 1, "Acción de prueba", "Venta")
        fila = db.fila(con.execute("SELECT * FROM bitacora"))
        self.assertEqual((fila["idUsuario"], fila["accion"], fila["entidad"]), (1, "Acción de prueba", "Venta"))
        self.assertRegex(fila["fecha"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        con.close()

    def test_mas_vendidos_respeta_el_limite(self):
        ranking = self.admin("reportes.mas_vendidos", limite=1)
        self.assertLessEqual(len(ranking), 1)


if __name__ == "__main__":
    unittest.main()
