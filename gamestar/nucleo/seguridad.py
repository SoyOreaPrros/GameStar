"""Cifrado de contraseñas: se almacenan como hash, nunca en texto plano (diccionario
de datos, clase Usuario). Usa PBKDF2-SHA256 de la biblioteca estándar, sin costos
ni dependencias adicionales (restricción 1.4.3)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

ITERACIONES = 200_000


def cifrar(contrasena: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), ITERACIONES).hex()
    return f"pbkdf2_sha256${ITERACIONES}${sal}${h}"


def verificar(contrasena: str, almacenado: str) -> bool:
    try:
        _, iteraciones, sal, h = almacenado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), int(iteraciones)).hex()
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(calc, h)
