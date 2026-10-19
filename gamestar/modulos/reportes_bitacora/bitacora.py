"""Bitácora de auditoría (RNF04).

Los demás módulos llaman a ``registrar`` dentro de la misma transacción de la
operación: si la operación se revierte, su registro también (no quedan registros de
acciones que no ocurrieron). La tabla tiene disparadores que impiden modificar o
borrar registros, por lo que la bitácora es inalterable.
"""

from __future__ import annotations

from gamestar.nucleo import db


def registrar(con, id_usuario: int, accion: str, entidad: str) -> int:
    cur = con.execute("INSERT INTO bitacora (idUsuario, accion, entidad, fecha) VALUES (?,?,?,?)",
                      (id_usuario, accion[:100], entidad[:50], db.ahora()))
    return cur.lastrowid
