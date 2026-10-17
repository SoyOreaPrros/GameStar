"""Lectura de ``config.ini``.

Infraestructura mínima (1.4.2): una computadora actúa como servidor con la base de
datos central y al menos dos laptops (una por sucursal) se conectan a ella (RNF07).

- En el servidor: ``python -m gamestar.servidor``
- En cada laptop: ``modo = red`` y la dirección del servidor; ``python -m gamestar``
- ``modo = local`` ejecuta todo en un solo equipo (útil para pruebas y demostración).
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = Path(os.environ.get("GAMESTAR_CONFIG", RAIZ / "config.ini"))


@dataclass
class Configuracion:
    modo: str = "local"                 # local | red
    servidor_host: str = "127.0.0.1"    # dirección del servidor (modo red)
    servidor_puerto: int = 8765
    escuchar_en: str = "0.0.0.0"        # interfaz en la que escucha el servidor
    base_datos: str = str(RAIZ / "datos" / "gamestar.db")
    tiempo_espera: float = 8.0          # segundos antes de considerar caída la red
    carpeta_comprobantes: str = str(RAIZ / "comprobantes")


def cargar(ruta: Path | str | None = None) -> Configuracion:
    cfg = Configuracion()
    p = Path(ruta) if ruta else ARCHIVO
    if p.exists():
        ini = configparser.ConfigParser()
        ini.read(p, encoding="utf-8")
        c = ini["conexion"] if ini.has_section("conexion") else {}
        s = ini["servidor"] if ini.has_section("servidor") else {}
        cfg.modo = c.get("modo", cfg.modo).strip().lower()
        cfg.servidor_host = c.get("servidor", cfg.servidor_host).strip()
        cfg.servidor_puerto = int(c.get("puerto", cfg.servidor_puerto))
        cfg.tiempo_espera = float(c.get("tiempo_espera", cfg.tiempo_espera))
        cfg.carpeta_comprobantes = _ruta(c.get("comprobantes", cfg.carpeta_comprobantes))
        cfg.escuchar_en = s.get("escuchar_en", cfg.escuchar_en).strip()
        cfg.servidor_puerto = int(s.get("puerto", cfg.servidor_puerto)) if "puerto" in s else cfg.servidor_puerto
        cfg.base_datos = _ruta(s.get("base_datos", cfg.base_datos))
    Path(cfg.base_datos).parent.mkdir(parents=True, exist_ok=True)
    return cfg


def _ruta(valor: str) -> str:
    p = Path(str(valor).strip())
    return str(p if p.is_absolute() else RAIZ / p)
