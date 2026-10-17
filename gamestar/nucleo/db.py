"""Acceso a la base de datos central (SQLite) y utilidades de datos.

Todas las operaciones que modifican datos se ejecutan dentro de una transacción
atómica: se completan por entero o se revierten por completo (RNF02, glosario
"Transacción atómica").
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .errores import ErrorValidacion

FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"  # aaaa-mm-dd hh:mm:ss (diccionario de datos)
FORMATO_FECHA = "%Y-%m-%d"  # aaaa-mm-dd

# Un candado por archivo serializa las escrituras dentro de un mismo proceso servidor,
# además del bloqueo propio de SQLite (BEGIN IMMEDIATE), para atender ventas
# simultáneas de ambas sucursales sin descuadre de stock (RNF07, concurrencia).
_candados: dict[str, threading.Lock] = {}
_candados_lock = threading.Lock()


def _candado(ruta: str) -> threading.Lock:
    with _candados_lock:
        return _candados.setdefault(ruta, threading.Lock())


def conectar(ruta: str) -> sqlite3.Connection:
    con = sqlite3.connect(ruta, timeout=15, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # integridad referencial (RFBD05, RFBD11)
    con.execute("PRAGMA busy_timeout = 15000")
    return con


@contextmanager
def transaccion(ruta: str, escritura: bool):
    """Abre una conexión; si es de escritura, la envuelve en una transacción atómica."""
    con = conectar(ruta)
    candado = _candado(ruta) if escritura else None
    try:
        if candado:
            candado.acquire()
            con.execute("BEGIN IMMEDIATE")
        try:
            yield con
        except BaseException:
            if escritura:
                con.execute("ROLLBACK")
            raise
        else:
            if escritura:
                con.execute("COMMIT")
    finally:
        if candado:
            candado.release()
        con.close()


def ahora() -> str:
    return datetime.now().strftime(FORMATO_FECHA_HORA)


def hoy() -> str:
    return date.today().strftime(FORMATO_FECHA)


# ---------------------------------------------------------------------------
# Importes. SQLite no tiene tipo DECIMAL; los importes (decimal con 2 decimales en
# el diccionario de datos) se guardan como enteros en centavos para que nunca haya
# errores de redondeo, y se exponen como texto con formato 0.00.
# ---------------------------------------------------------------------------

def a_centavos(valor, campo: str = "Precio") -> int:
    try:
        d = Decimal(str(valor).strip().replace(",", ""))
    except (InvalidOperation, AttributeError):
        raise ErrorValidacion(f"{campo}: escribe un número con formato 0.00.") from None
    if not d.is_finite():
        raise ErrorValidacion(f"{campo}: escribe un número con formato 0.00.")
    if d != d.quantize(Decimal("0.01")):
        raise ErrorValidacion(f"{campo}: usa como máximo 2 decimales.")
    centavos = int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))
    if abs(centavos) >= 10**10:  # 10 dígitos en total
        raise ErrorValidacion(f"{campo}: el importe es demasiado grande.")
    return centavos


def de_centavos(centavos: int) -> str:
    return f"{Decimal(centavos) / 100:.2f}"


def entero(valor, campo: str, minimo: int | None = None) -> int:
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ErrorValidacion(f"{campo}: escribe un número entero.") from None
    if minimo is not None and n < minimo:
        raise ErrorValidacion(f"{campo}: debe ser mayor o igual que {minimo}.")
    return n


def texto(valor, campo: str, maximo: int, obligatorio: bool = True) -> str:
    t = ("" if valor is None else str(valor)).strip()
    if obligatorio and not t:
        raise ErrorValidacion(f"{campo}: es un dato obligatorio.")
    if len(t) > maximo:
        raise ErrorValidacion(f"{campo}: máximo {maximo} caracteres.")
    return t


def filas(cursor) -> list[dict]:
    return [dict(f) for f in cursor.fetchall()]


def fila(cursor) -> dict | None:
    f = cursor.fetchone()
    return dict(f) if f else None
