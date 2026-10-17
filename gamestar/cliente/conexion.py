"""Conexión de la interfaz con la lógica de negocio.

``ConexionRed`` habla con el servidor central por HTTP/JSON (arquitectura
cliente-servidor, RNF07). ``ConexionLocal`` ejecuta los mismos servicios en el
propio equipo. La interfaz solo conoce el método ``llamar``, por lo que la lógica
de negocio queda separada de la interfaz (RNF06).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from gamestar.nucleo.errores import TIPOS, ErrorConexion, ErrorGameStar


class Conexion:
    token: str | None = None

    def llamar(self, servicio: str, **args):
        raise NotImplementedError

    def describir(self) -> str:
        raise NotImplementedError


class ConexionLocal(Conexion):
    def __init__(self, ruta_db: str):
        from gamestar.nucleo.servicios import Despachador

        self.despachador = Despachador(ruta_db)
        self.token = None

    def llamar(self, servicio: str, **args):
        return self.despachador.ejecutar(servicio, self.token, args)

    def describir(self) -> str:
        return "Modo local"


class ConexionRed(Conexion):
    def __init__(self, host: str, puerto: int, tiempo_espera: float = 8.0):
        self.url = f"http://{host}:{puerto}/rpc"
        self.tiempo_espera = tiempo_espera
        self.token = None
        # El servidor está en la red de la tienda: no se usa ningún proxy del sistema.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def llamar(self, servicio: str, **args):
        cuerpo = json.dumps({"servicio": servicio, "token": self.token, "args": args}).encode("utf-8")
        peticion = urllib.request.Request(self.url, data=cuerpo, method="POST",
                                          headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with self._opener.open(peticion, timeout=self.tiempo_espera) as r:
                respuesta = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError):
            raise ErrorConexion(
                "No hay conexión con el servidor. La operación no se completó; "
                "verifica la red e inténtalo de nuevo.") from None
        if respuesta.get("ok"):
            return respuesta.get("resultado")
        clase = TIPOS.get(respuesta.get("tipo"), ErrorGameStar)
        raise clase(respuesta.get("error", "Error desconocido en el servidor."))

    def describir(self) -> str:
        return self.url.replace("/rpc", "")


def crear(cfg) -> Conexion:
    if cfg.modo == "red":
        return ConexionRed(cfg.servidor_host, cfg.servidor_puerto, cfg.tiempo_espera)
    return ConexionLocal(cfg.base_datos)
