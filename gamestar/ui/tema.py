"""Identidad visual tomada del prototipo "GameStar Diseño Final".

El resultado 1 de la evaluación del prototipo (2.2.3) pidió usar los colores del
logotipo del negocio: negro, rojo y plata sobre fondo gris claro.
"""

from __future__ import annotations

import tkinter.font as tkfont

FONDO = "#EBECEE"
BLANCO = "#FFFFFF"
BORDE = "#D6D8DC"
BORDE_CAMPO = "#9C9FA6"
SEPARADOR = "#E6E7EA"
TEXTO = "#18181B"
TEXTO_TENUE = "#5E6169"
TEXTO_CAPS = "#55585F"
MARCADOR = "#8A8D94"          # texto de ejemplo en campos vacíos
ROJO = "#C8191C"
ROJO_OSCURO = "#A51418"
ROJO_TEXTO = "#8B1015"
ROJO_SUAVE = "#FAD7D8"
NEGRO = "#111114"
NEGRO_PASTILLA = "#2A2A2E"
PLATA = "#E4E5E8"
PLATA_BORDE = "#A8ABB0"
AMARILLO = "#F7EBA8"
AMARILLO_BORDE = "#D6C266"
AMARILLO_TEXTO = "#4A3B00"
FILA_SELECCION = "#ECEDEF"
BARRA_VACIA = "#E4E5E8"

ESTILOS_PASTILLA = {
    # estilo: (relleno, borde, texto)
    "plata": (PLATA, PLATA_BORDE, "#3A3C41"),
    "negro": (NEGRO_PASTILLA, NEGRO_PASTILLA, BLANCO),
    "rojo": (ROJO_SUAVE, ROJO, ROJO_TEXTO),
    "amarillo": (AMARILLO, AMARILLO_BORDE, AMARILLO_TEXTO),
}

_FAMILIAS = ("DM Sans", "Segoe UI", "Inter", "Helvetica Neue", "Arial", "DejaVu Sans")
_fuentes: dict[str, tkfont.Font] = {}


def familia() -> str:
    disponibles = {f.lower(): f for f in tkfont.families()}
    return next((disponibles[f.lower()] for f in _FAMILIAS if f.lower() in disponibles), "TkDefaultFont")


def fuente(nombre: str) -> tkfont.Font:
    """Fuentes con tamaño en píxeles (valores negativos) para que se vean iguales en
    cualquier equipo."""
    if not _fuentes:
        f = familia()
        especificacion = {
            "titulo": (-22, "bold"),
            "titulo_tarjeta": (-19, "bold"),
            "seccion": (-18, "bold"),
            "cuerpo": (-15, "normal"),
            "cuerpo_negrita": (-15, "bold"),
            "tenue": (-14, "normal"),
            "etiqueta": (-14, "bold"),
            "caps": (-12, "bold"),
            "boton": (-16, "bold"),
            "pastilla": (-13, "bold"),
            "enlace": (-15, "bold"),
            "enlace_normal": (-16, "normal"),
            "dato": (-17, "normal"),
            "grande": (-18, "bold"),
            "numero": (-15, "bold"),
        }
        for clave, (tam, peso) in especificacion.items():
            _fuentes[clave] = tkfont.Font(family=f, size=tam, weight=peso)
    return _fuentes[nombre]
