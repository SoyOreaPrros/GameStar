"""Reglas del dominio compartidas por varios módulos (glosario del documento)."""

from __future__ import annotations

# "Stock bajo: condición en que el stock es menor o igual a cinco unidades o queda bajo
# el stock mínimo" (glosario 1.1.3.c, RF07, RFBD12, CU-16 y nota del prototipo).
LIMITE_STOCK_BAJO = 5

ESTADOS_REPARACION = ("PENDIENTE", "EN_PROCESO", "TERMINADA")  # RFBD10
NOMBRE_ESTADO = {"PENDIENTE": "Pendiente", "EN_PROCESO": "En proceso", "TERMINADA": "Terminada"}


def es_stock_bajo(existencia: int, stock_minimo: int) -> bool:
    return existencia <= LIMITE_STOCK_BAJO or existencia < stock_minimo


SQL_STOCK_BAJO = f"(i.existencia <= {LIMITE_STOCK_BAJO} OR i.existencia < p.stockMinimo)"
