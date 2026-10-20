"""Pruebas de la rama feature/inventario (CU-02, CU-07, CU-08, CU-09, CU-16)."""

import time
import unittest

from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorPermiso, ErrorValidacion
from tests.base import CasoGameStar


class PruebasInventario(CasoGameStar):
    def setUp(self):
        super().setUp()
        self.admin = self.crear_admin()  # sucursal 1
        self.admin("usuarios.registrar", nombre="Emp", usuarioAcceso="emp", contrasena="1", rol="EMPLEADO", idSucursal=1)
        self.emp = self.entrar("emp", "1")

    def producto(self, nombre="Zelda TOTK", cat=1, precio="1299.00", minimo=2, inicial=10):
        return self.admin("inventario.registrar_producto", nombre=nombre, idCategoria=cat, precio=precio,
                          stockMinimo=minimo, cantidadInicial=inicial)["idProducto"]

    def test_registrar_crea_existencia_por_sucursal_rfbd03(self):
        pid = self.producto()
        r = self.emp("inventario.consultar")
        p = r["productos"][0]
        self.assertEqual(p["idProducto"], pid)
        self.assertEqual(p["existencias"], {"1": 10, "2": 0})
        self.assertEqual(p["precio"], "1299.00")
        con = db.conectar(self.ruta)
        self.assertEqual(con.execute("SELECT tipo, cantidad FROM movimientoinventario").fetchall()[0][:], ("ENTRADA", 10))
        self.assertEqual(con.execute("SELECT entidad FROM bitacora").fetchone()[0], "Producto")
        con.close()

    def test_validaciones_cu07(self):
        for kw in ({"precio": "0"}, {"precio": "-5"}, {"precio": "abc"}, {"nombre": ""}, {"cat": 99}, {"minimo": -1}):
            datos = {"nombre": "X", "cat": 1, "precio": "10", "minimo": 0, "inicial": 0} | kw
            with self.assertRaises(ErrorValidacion):
                self.producto(**datos)

    def test_buscar_y_filtrar_rf05_rf06(self):
        self.producto("The Legend of Zelda", 1)
        self.producto("Control DualSense", 3)
        self.producto("Nintendo Switch", 2)
        nombres = lambda r: [p["nombre"] for p in r["productos"]]
        self.assertEqual(nombres(self.emp("inventario.consultar", texto="zelda")), ["The Legend of Zelda"])
        self.assertEqual(nombres(self.emp("inventario.consultar", texto="ZÉLDA")), ["The Legend of Zelda"])
        self.assertEqual(nombres(self.emp("inventario.consultar", idCategoria=2)), ["Nintendo Switch"])
        self.assertEqual(nombres(self.emp("inventario.consultar", texto="xyz")), [])

    def test_stock_bajo_rf07(self):
        self.producto("Poco", inicial=5, minimo=0)
        self.producto("Bajo mínimo", inicial=8, minimo=10)
        self.producto("Suficiente", inicial=20, minimo=3)
        bajos = {p["nombre"]: p["stockBajo"] for p in self.emp("inventario.consultar")["productos"]}
        self.assertEqual(bajos, {"Poco": True, "Bajo mínimo": True, "Suficiente": True})  # sucursal 2 en 0
        alertas = {(a["nombre"], a["sucursal"]) for a in self.admin("inventario.alertas")}
        self.assertIn(("Poco", "Sucursal 1"), alertas)
        self.assertNotIn(("Suficiente", "Sucursal 1"), alertas)
        self.assertEqual(self.admin("inventario.contar_alertas"), len(alertas))
        self.assertTrue(all("categoria" in a for a in self.admin("inventario.alertas")))

    def test_modificar_y_ajustar_minimo_cu08(self):
        pid = self.producto()
        self.admin("inventario.modificar_producto", idProducto=pid, nombre="Zelda", idCategoria=1, precio="999.50", stockMinimo=4)
        self.admin("inventario.ajustar_stock_minimo", idProducto=pid, stockMinimo=7)
        p = self.admin("inventario.catalogo")[0]
        self.assertEqual((p["nombre"], p["precio"], p["stockMinimo"]), ("Zelda", "999.50", 7))

    def test_entrada_de_mercancia(self):
        pid = self.producto(inicial=0)
        self.admin("inventario.registrar_entrada", idProducto=pid, idSucursal=2, cantidad=6)
        self.assertEqual(self.emp("inventario.consultar")["productos"][0]["existencias"], {"1": 0, "2": 6})
        movs = self.admin("inventario.movimientos")
        self.assertEqual((movs[0]["tipo"], movs[0]["cantidad"], movs[0]["sucursal"]), ("ENTRADA", 6, "Sucursal 2"))

    def test_eliminar_protege_integridad_rfbd11(self):
        sin_historial = self.producto("Nuevo", inicial=0)
        con_existencia = self.producto("Con stock", inicial=3)
        self.admin("inventario.eliminar_producto", idProducto=sin_historial)
        with self.assertRaises(ErrorValidacion):
            self.admin("inventario.eliminar_producto", idProducto=con_existencia)
        self.assertEqual([p["nombre"] for p in self.admin("inventario.catalogo")], ["Con stock"])

    def test_permisos_rnf03(self):
        for servicio, args in (("inventario.registrar_producto", {}), ("inventario.alertas", {}),
                               ("inventario.movimientos", {}), ("inventario.catalogo", {})):
            with self.assertRaises(ErrorPermiso):
                self.emp(servicio, **args)

    def test_consulta_en_menos_de_2_segundos_rnf01(self):
        con = db.conectar(self.ruta)
        con.execute("BEGIN")
        for i in range(3000):
            cur = con.execute("INSERT INTO producto (nombre, precio, stockMinimo, idCategoria) VALUES (?,?,?,?)",
                              (f"Producto {i}", 1000, 1, 1 + i % 3))
            con.execute("INSERT INTO inventario (idProducto, idSucursal, existencia) VALUES (?,1,?),(?,2,?)",
                        (cur.lastrowid, i % 20, cur.lastrowid, i % 7))
        con.execute("COMMIT")
        con.close()
        inicio = time.perf_counter()
        r = self.emp("inventario.consultar", texto="producto 29")
        self.assertLess(time.perf_counter() - inicio, 2.0)
        self.assertTrue(r["productos"])


if __name__ == "__main__":
    unittest.main()
