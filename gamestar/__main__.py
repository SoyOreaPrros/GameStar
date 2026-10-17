"""Inicia la aplicación de escritorio de GameStar en una laptop de sucursal.

    python -m gamestar
"""

from __future__ import annotations

import sys


def main() -> int:
    from gamestar import config
    from gamestar.cliente.conexion import crear
    from gamestar.ui.app import App

    cfg = config.cargar()
    app = App(crear(cfg), cfg)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
