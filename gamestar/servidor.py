"""Servidor central de GameStar.

Se ejecuta en la computadora que actúa como servidor (1.4.2) y atiende a las
laptops de las sucursales de forma simultánea (RNF07). Solo usa la biblioteca
estándar de Python: no requiere pagos, suscripciones ni costos extra (1.4.3).

    python -m gamestar.servidor
"""

from __future__ import annotations

import json
import logging
import socket
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gamestar import config
from gamestar.nucleo.errores import ErrorGameStar
from gamestar.nucleo.servicios import Despachador

log = logging.getLogger("gamestar.servidor")
TAMANO_MAXIMO = 2 * 1024 * 1024


def crear_manejador(despachador: Despachador):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "GameStar/1.0"

        def log_message(self, formato, *args):  # registro en consola del servidor
            log.info("%s %s", self.address_string(), formato % args)

        def _responder(self, codigo: int, cuerpo: dict):
            datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            if self.path == "/estado":
                self._responder(200, {"ok": True, "resultado": "GameStar en línea"})
            else:
                self._responder(404, {"ok": False, "error": "Ruta no encontrada"})

        def do_POST(self):
            if self.path != "/rpc":
                self._responder(404, {"ok": False, "error": "Ruta no encontrada"})
                return
            try:
                largo = int(self.headers.get("Content-Length", "0"))
                if largo <= 0 or largo > TAMANO_MAXIMO:
                    raise ValueError
                peticion = json.loads(self.rfile.read(largo).decode("utf-8"))
                nombre = str(peticion["servicio"])
                args = peticion.get("args") or {}
                if not isinstance(args, dict):
                    raise ValueError
            except (ValueError, KeyError, UnicodeDecodeError):
                self._responder(400, {"ok": False, "tipo": "error", "error": "Petición mal formada."})
                return
            try:
                resultado = despachador.ejecutar(nombre, peticion.get("token"), args)
                self._responder(200, {"ok": True, "resultado": resultado})
            except ErrorGameStar as e:
                self._responder(200, {"ok": False, "tipo": e.tipo, "error": e.mensaje})
            except Exception:  # error no previsto: la transacción ya se revirtió
                log.error("Error interno en %s\n%s", nombre, traceback.format_exc())
                self._responder(500, {"ok": False, "tipo": "error",
                                      "error": "Error interno del servidor. La operación no se guardó."})

    return Manejador


def iniciar(cfg=None) -> ThreadingHTTPServer:
    cfg = cfg or config.cargar()
    despachador = Despachador(cfg.base_datos)
    servidor = ThreadingHTTPServer((cfg.escuchar_en, cfg.servidor_puerto), crear_manejador(despachador))
    servidor.daemon_threads = True
    return servidor


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cfg = config.cargar()
    servidor = iniciar(cfg)
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        ip = "127.0.0.1"
    print(f"Servidor GameStar escuchando en {cfg.escuchar_en}:{cfg.servidor_puerto}")
    print(f"Base de datos: {cfg.base_datos}")
    print(f"En cada laptop configure: modo = red, servidor = {ip}, puerto = {cfg.servidor_puerto}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    sys.exit(main())
