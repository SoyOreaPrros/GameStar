"""Pruebas de la rama feature/ventas (CU-03, CU-13, RFBD04 a RFBD07, RNF02, RNF04)."""

import tempfile
import unittest
import uuid
from pathlib import Path

from gamestar.modulos.ventas.comprobante import guardar_comprobante
from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorPermiso, ErrorValidacion
from tests.base import CasoGameStar


class PruebasVentas(CasoGameStar):
    def setUp(self):
        super().setUp()
        self.admin = self.crear_admin()
        self.admin("usuarios.registrar", nombre="Emp Uno", usuarioAcceso="emp", contrasena="1", rol="EMPLEADO", idSucursal=1)
        self.emp = self.entrar("emp", "1")
        self.juego = self.admin("inventario.registrar_producto", nombre="Mario Kart", idCategoria=1, precio="1099.00",
                                stockMinimo=2, cantidadInicial=8)["idProducto"]
        self.control = self.admin("inventario.registrar_producto", nombre="Control Pro", idCategoria=3, precio="1499.50",
                                  stockMinimo=1, cantidadInicial=3)["idProducto"]

    def vender(self, lineas, clave=None):
        return self.emp("ventas.registrar", lineas=lineas, claveOperacion=clave or uuid.uuid4().hex)

    def existencia(self, pid, suc=1):
        con = db.conectar(self.ruta)
        n = con.execute("SELECT existencia FROM inventario WHERE idProducto=? AND idSucursal=?", (pid, suc)).fetchone()[0]
        con.close()
        return n

    def test_registrar_venta_completa(self):
        v = self.vender([{"idProducto": self.juego, "cantidad": 2}, {"idProducto": self.control, "cantidad": 1}])
        self.assertEqual(v["total"], "3697.50")
        self.assertEqual(v["usuario"], "Emp Uno")
        self.assertEqual(v["sucursal"], "Sucursal 1")
        self.assertEqual(self.existencia(self.juego), 6)       # RF09 / RFBD06
        self.assertEqual(self.existencia(self.control), 2)
        con = db.conectar(self.ruta)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM movimientoinventario WHERE tipo='SALIDA'").fetchone()[0], 2)  # RFBD07
        self.assertEqual(con.execute("SELECT COUNT(*) FROM bitacora WHERE entidad='Venta'").fetchone()[0], 1)  # RNF04
        con.close()
        self.assertEqual({p["nombre"] for p in v["stockBajo"]}, {"Control Pro"})  # RF07: 2 <= 5

    def test_precio_historico_rfbd04(self):
        v = self.vender([{"idProducto": self.juego, "cantidad": 1}])
        self.admin("inventario.modificar_producto", idProducto=self.juego, nombre="Mario Kart", idCategoria=1,
                   precio="1500.00", stockMinimo=2)
        d = self.admin("ventas.detalle", idVenta=v["idVenta"])
        self.assertEqual(d["renglones"][0]["precioUnitario"], "1099.00")
        self.assertEqual(d["total"], "1099.00")

    def test_cantidad_mayor_a_existencia_revierte_todo(self):
        with self.assertRaises(ErrorValidacion):
            self.vender([{"idProducto": self.juego, "cantidad": 1}, {"idProducto": self.control, "cantidad": 4}])
        self.assertEqual(self.existencia(self.juego), 8)  # transacción atómica: nada se guardó
        self.assertEqual(self.admin("ventas.historial"), [])

    def test_reintento_no_duplica_rnf02(self):
        clave = uuid.uuid4().hex
        v1 = self.vender([{"idProducto": self.juego, "cantidad": 1}], clave)
        v2 = self.vender([{"idProducto": self.juego, "cantidad": 1}], clave)
        self.assertEqual(v1["idVenta"], v2["idVenta"])
        self.assertTrue(v2["repetida"])
        self.assertEqual(self.existencia(self.juego), 7)
        self.assertEqual(len(self.admin("ventas.historial")), 1)

    def test_venta_vacia_o_invalida(self):
        for lineas in ([], [{"idProducto": self.juego, "cantidad": 0}], [{"idProducto": 999, "cantidad": 1}]):
            with self.assertRaises(ErrorValidacion):
                self.vender(lineas)

    def test_historial_y_permisos_cu13(self):
        self.vender([{"idProducto": self.juego, "cantidad": 3}])
        h = self.admin("ventas.historial")
        self.assertEqual((h[0]["usuario"], h[0]["sucursal"], h[0]["total"]), ("Emp Uno", "Sucursal 1", "3297.00"))
        with self.assertRaises(ErrorPermiso):
            self.emp("ventas.historial")
        with self.assertRaises(ErrorPermiso):  # el registro de ventas es función del empleado
            self.admin("ventas.registrar", lineas=[{"idProducto": self.juego, "cantidad": 1}], claveOperacion="x")

    def test_mas_vendidos_y_reporte(self):
        self.vender([{"idProducto": self.juego, "cantidad": 3}])
        self.vender([{"idProducto": self.control, "cantidad": 1}])
        top = self.admin("reportes.mas_vendidos")
        self.assertEqual([(p["nombre"], p["unidades"]) for p in top], [("Mario Kart", 3), ("Control Pro", 1)])
        r = self.admin("reportes.generar", tipo="VENTAS")
        self.assertEqual(len(r["filas"]), 2)
        self.assertIn(("Total vendido", "4796.50"), [tuple(x) for x in r["resumen"]])

    def test_comprobante(self):
        v = self.vender([{"idProducto": self.juego, "cantidad": 2}])
        with tempfile.TemporaryDirectory() as d:
            ruta = guardar_comprobante(v, Path(d))
            texto = ruta.read_text(encoding="utf-8")
        self.assertIn("Mario Kart", texto)
        self.assertIn("2198.00", texto)

    def test_productos_con_existencia_de_la_sucursal(self):
        productos = self.emp("ventas.productos", texto="mario")
        self.assertEqual([p["nombre"] for p in productos], ["Mario Kart"])
        self.assertEqual(productos[0]["existencia"], 8)


if __name__ == "__main__":
    unittest.main()
