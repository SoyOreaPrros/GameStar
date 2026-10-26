"""Pruebas de la rama feature/reparaciones (CU-04, CU-05, CU-06, CU-14, RFBD08, RFBD10)."""

import unittest

from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorPermiso, ErrorValidacion
from tests.base import CasoGameStar


class PruebasReparaciones(CasoGameStar):
    def setUp(self):
        super().setUp()
        self.admin = self.crear_admin()
        self.admin("usuarios.registrar", nombre="Técnico", usuarioAcceso="tec", contrasena="1", rol="EMPLEADO", idSucursal=2)
        self.emp = self.entrar("tec", "1")
        self.pieza = self.admin("inventario.registrar_producto", nombre="Joystick analógico", idCategoria=3, precio="150",
                                stockMinimo=2, cantidadInicial=0)["idProducto"]
        self.admin("inventario.registrar_entrada", idProducto=self.pieza, idSucursal=2, cantidad=9)

    def nueva(self, **kw):
        datos = {"cliente": "Luis Pérez", "telefono": "228 123 4567", "equipo": "PS5", "falla": "No da imagen"} | kw
        return self.emp("reparaciones.registrar", **datos)

    def test_registrar_cu04(self):
        r = self.nueva()
        self.assertEqual((r["estado"], r["sucursal"], r["usuario"]), ("PENDIENTE", "Sucursal 2", "Técnico"))
        self.assertIsNone(r["fechaEntrega"])
        self.assertTrue(r["fechaIngreso"])

    def test_datos_obligatorios(self):
        for campo in ("cliente", "telefono", "equipo", "falla"):
            with self.assertRaises(ErrorValidacion):
                self.nueva(**{campo: "  "})

    def test_estados_validos_rfbd10(self):
        r = self.nueva()
        r = self.emp("reparaciones.actualizar_estado", idReparacion=r["idReparacion"], estado="EN_PROCESO")
        self.assertEqual(r["nombreEstado"], "En proceso")
        with self.assertRaises(ErrorValidacion):
            self.emp("reparaciones.actualizar_estado", idReparacion=r["idReparacion"], estado="PERDIDA")
        con = db.conectar(self.ruta)
        self.assertTrue(con.execute("SELECT 1 FROM bitacora WHERE accion LIKE 'Cambiar estado%'").fetchone())  # RNF04
        con.close()

    def test_refaccion_descuenta_inventario_rfbd08(self):
        r = self.nueva()
        r = self.emp("reparaciones.registrar_refaccion", idReparacion=r["idReparacion"], idProducto=self.pieza, cantidad=2)
        self.assertEqual(r["existenciaRestante"], 7)
        self.assertEqual([(x["nombre"], x["cantidad"]) for x in r["refacciones"]], [("Joystick analógico", 2)])
        with self.assertRaises(ErrorValidacion):
            self.emp("reparaciones.registrar_refaccion", idReparacion=r["idReparacion"], idProducto=self.pieza, cantidad=50)
        self.assertEqual(len(self.emp("reparaciones.obtener", idReparacion=r["idReparacion"])["refacciones"]), 1)
        movs = self.admin("inventario.movimientos")
        self.assertEqual((movs[0]["tipo"], movs[0]["cantidad"]), ("SALIDA", 2))

    def test_entrega_solo_terminada_cu06(self):
        r = self.nueva()
        with self.assertRaises(ErrorValidacion):
            self.emp("reparaciones.registrar_entrega", idReparacion=r["idReparacion"], fechaEntrega="25/10/2026")
        self.emp("reparaciones.actualizar_estado", idReparacion=r["idReparacion"], estado="TERMINADA")
        with self.assertRaises(ErrorValidacion):
            self.emp("reparaciones.registrar_entrega", idReparacion=r["idReparacion"], fechaEntrega="2026/31/12")
        r = self.emp("reparaciones.registrar_entrega", idReparacion=r["idReparacion"], fechaEntrega="25/10/2026")
        self.assertEqual(r["fechaEntrega"], "2026-10-25")

    def test_buscar_y_consultar_cu14(self):
        a = self.nueva(cliente="Ana Ruiz", telefono="2281112233", equipo="Switch")
        self.nueva(cliente="Beto", equipo="Xbox Series")
        self.assertEqual([r["cliente"] for r in self.emp("reparaciones.buscar", texto="ruiz")], ["Ana Ruiz"])
        self.assertEqual([r["cliente"] for r in self.emp("reparaciones.buscar", texto="2281112233")], ["Ana Ruiz"])
        self.assertEqual([r["cliente"] for r in self.emp("reparaciones.buscar", texto=f"#{a['idReparacion']}")], ["Ana Ruiz"])
        lista = self.admin("reparaciones.listar")
        self.assertEqual(len(lista), 2)
        self.assertIn("telefono", lista[0])
        with self.assertRaises(ErrorPermiso):
            self.emp("reparaciones.listar")
        with self.assertRaises(ErrorPermiso):
            self.admin("reparaciones.registrar", cliente="x", telefono="1", equipo="e", falla="f")

    def test_reporte_reparaciones(self):
        self.nueva()
        r = self.admin("reportes.generar", tipo="REPARACIONES")
        self.assertEqual(r["filas"][0][1], "Luis Pérez")
        self.assertIsNone(r["aviso"])

    def test_refacciones_disponibles_de_la_sucursal(self):
        r = self.nueva()
        refacciones = self.emp("reparaciones.refacciones_disponibles", idReparacion=r["idReparacion"])
        self.assertEqual([f["nombre"] for f in refacciones], ["Joystick analógico"])
        self.assertEqual(self.emp("reparaciones.refacciones_disponibles", idReparacion=r["idReparacion"],
                                  texto="zzz"), [])


if __name__ == "__main__":
    unittest.main()
