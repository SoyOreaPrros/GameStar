"""Registro de venta emitido como comprobante digital (glosario "Comprobante / Ticket").

Está separado de la interfaz para poder probarlo y reutilizarlo (RNF06)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from gamestar import NOMBRE_SISTEMA


def guardar_comprobante(v: dict, carpeta: Path) -> Path:
    """Comprobante digital de la venta (glosario "Comprobante / Ticket")."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ancho = 44
    lineas = [NOMBRE_SISTEMA.center(ancho), "Registro de venta".center(ancho), "=" * ancho,
              f"Folio:    {v['idVenta']}", f"Fecha:    {v['fecha']}", f"Sucursal: {v['sucursal']}",
              f"Atendió:  {v['usuario']}", "-" * ancho, f"{'Producto':<22}{'Cant':>5}{'P. unit':>8}{'Importe':>9}", "-" * ancho]
    for r in v["renglones"]:
        nombre = r["nombre"]
        lineas.append(f"{nombre[:22]:<22}{r['cantidad']:>5}{r['precioUnitario']:>8}{r['importe']:>9}")
        for resto in (nombre[i:i + 22] for i in range(22, len(nombre), 22)):
            lineas.append(resto)
    lineas += ["-" * ancho, f"{'TOTAL':<30}{v['total']:>14}", "=" * ancho]
    ruta = carpeta / f"venta_{int(v['idVenta']):06d}.txt"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def abrir(ruta: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(ruta)])
        else:
            subprocess.Popen(["xdg-open", str(ruta)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
