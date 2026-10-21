"""Pruebas de la arquitectura cliente-servidor (RNF07) y del manejo de caída de red (RNF02)."""

import os
import tempfile
import threading
import unittest

from gamestar import config, servidor
from gamestar.cliente.conexion import ConexionRed
from gamestar.nucleo.errores import ErrorConexion, ErrorPermiso, ErrorValidacion


class PruebasServidor(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        cfg = config.Configuracion(base_datos=os.path.join(self._dir.name, "s.db"), escuchar_en="127.0.0.1",
                                   servidor_puerto=0)
        self.srv = servidor.iniciar(cfg)
        self.puerto = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self._dir.cleanup()

    def cliente(self):
        return ConexionRed("127.0.0.1", self.puerto, 5)

    def test_dos_laptops_venden_a_la_vez_sin_descuadre(self):
        admin = self.cliente()
        admin.llamar("usuarios.crear_administrador_inicial", nombre="Dueño", usuarioAcceso="admin", contrasena="a", idSucursal=1)
        admin.token = admin.llamar("usuarios.iniciar_sesion", usuarioAcceso="admin", contrasena="a")["token"]
        pid = admin.llamar("inventario.registrar_producto", nombre="Juego", idCategoria=1, precio="100",
                           stockMinimo=0, cantidadInicial=40)["idProducto"]
        laptops = []
        for i in (1, 2):
            admin.llamar("usuarios.registrar", nombre=f"E{i}", usuarioAcceso=f"e{i}", contrasena="1", rol="EMPLEADO", idSucursal=1)
            c = self.cliente()
            c.token = c.llamar("usuarios.iniciar_sesion", usuarioAcceso=f"e{i}", contrasena="1")["token"]
            laptops.append(c)
        errores = []

        def vender(c, n):
            for k in range(n):
                try:
                    c.llamar("ventas.registrar", lineas=[{"idProducto": pid, "cantidad": 1}], claveOperacion=f"{id(c)}-{k}")
                except ErrorValidacion:
                    errores.append(1)

        hilos = [threading.Thread(target=vender, args=(c, 25)) for c in laptops]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        vendidas = len(admin.llamar("ventas.historial"))
        existencia = admin.llamar("inventario.consultar")["productos"][0]["existencias"]["1"]
        self.assertEqual(vendidas, 40)
        self.assertEqual(existencia, 0)
        self.assertEqual(len(errores), 10)  # las ventas sin existencia se rechazan completas

    def test_errores_de_negocio_viajan_al_cliente(self):
        c = self.cliente()
        c.llamar("usuarios.crear_administrador_inicial", nombre="D", usuarioAcceso="d", contrasena="d", idSucursal=1)
        with self.assertRaises(ErrorValidacion):
            c.llamar("usuarios.iniciar_sesion", usuarioAcceso="d", contrasena="mala")
        c.token = c.llamar("usuarios.iniciar_sesion", usuarioAcceso="d", contrasena="d")["token"]
        with self.assertRaises(ErrorPermiso):
            c.llamar("ventas.registrar", lineas=[], claveOperacion="x")

    def test_sin_servidor(self):
        c = ConexionRed("127.0.0.1", 1, 1)
        with self.assertRaises(ErrorConexion):
            c.llamar("usuarios.estado_inicial")


if __name__ == "__main__":
    unittest.main()
