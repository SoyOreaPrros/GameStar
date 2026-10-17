"""Pruebas del núcleo: esquema, bitácora inalterable, importes y contraseñas."""

import sqlite3
import unittest

from gamestar.nucleo import db, esquema, seguridad
from gamestar.nucleo.errores import ErrorValidacion
from gamestar.nucleo.reglas import es_stock_bajo
from tests.base import CasoGameStar


class PruebasEsquema(CasoGameStar):
    def test_datos_base(self):
        con = db.conectar(self.ruta)
        self.assertEqual([r[0] for r in con.execute("SELECT nombre FROM sucursal ORDER BY idSucursal")],
                         list(esquema.SUCURSALES_BASE))
        self.assertEqual(len(con.execute("SELECT * FROM categoria").fetchall()), 3)
        con.close()

    def test_inicializar_dos_veces_no_duplica(self):
        esquema.inicializar(self.ruta)
        con = db.conectar(self.ruta)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM sucursal").fetchone()[0], 2)
        con.close()

    def test_rol_restringido_rfbd02(self):
        con = db.conectar(self.ruta)
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO usuario (nombre, usuarioAcceso, contrasena, rol, idSucursal) "
                        "VALUES ('x','x','x','GERENTE',1)")
        con.close()

    def test_estado_reparacion_restringido_rfbd10(self):
        con = db.conectar(self.ruta)
        con.execute("INSERT INTO usuario (nombre, usuarioAcceso, contrasena, rol, idSucursal) VALUES ('a','a','h','EMPLEADO',1)")
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO reparacion (cliente, telefono, equipo, falla, estado, fechaIngreso, idUsuario, idSucursal) "
                        "VALUES ('c','1','e','f','PERDIDA','2026-01-01 00:00:00',1,1)")
        con.close()

    def test_bitacora_inalterable_rnf04(self):
        con = db.conectar(self.ruta)
        con.execute("INSERT INTO usuario (nombre, usuarioAcceso, contrasena, rol, idSucursal) VALUES ('a','a','h','EMPLEADO',1)")
        con.execute("INSERT INTO bitacora (idUsuario, accion, entidad, fecha) VALUES (1,'x','Venta','2026-01-01 00:00:00')")
        with self.assertRaises(sqlite3.DatabaseError):
            con.execute("UPDATE bitacora SET accion = 'y'")
        with self.assertRaises(sqlite3.DatabaseError):
            con.execute("DELETE FROM bitacora")
        con.close()


class PruebasUtilidades(unittest.TestCase):
    def test_importes_en_centavos(self):
        self.assertEqual(db.a_centavos("199.90"), 19990)
        self.assertEqual(db.de_centavos(19990), "199.90")
        self.assertEqual(db.a_centavos("1,299.5"), 129950)
        for malo in ("abc", "1.999", "", "nan"):
            with self.assertRaises(ErrorValidacion):
                db.a_centavos(malo)

    def test_contrasena_con_hash(self):
        h = seguridad.cifrar("secreta")
        self.assertNotIn("secreta", h)
        self.assertTrue(seguridad.verificar("secreta", h))
        self.assertFalse(seguridad.verificar("otra", h))

    def test_regla_stock_bajo(self):
        self.assertTrue(es_stock_bajo(5, 0))      # cinco unidades o menos
        self.assertFalse(es_stock_bajo(6, 0))
        self.assertTrue(es_stock_bajo(9, 10))     # bajo el stock mínimo
        self.assertFalse(es_stock_bajo(10, 10))


if __name__ == "__main__":
    unittest.main()
