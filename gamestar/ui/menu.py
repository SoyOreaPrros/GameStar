"""Menú principal por rol (2.2.2.C.a y menú del administrador del diseño final).

Muestra únicamente las funciones permitidas para el rol de la sesión (RNF03). Las
tarjetas las registra cada módulo integrado.
"""

from __future__ import annotations

import tkinter as tk

from . import tema as t
from . import widgets as w
from .app import NOMBRE_ROL, ROL_ADMINISTRADOR, TIPO_FUNCION, Pantalla


class MenuPrincipal(Pantalla):
    volver = None

    def titulo(self):
        return f"Menú principal · {NOMBRE_ROL[self.app.usuario['rol']]}"

    def construir(self):
        rol = self.app.usuario["rol"]
        tarjetas = sorted((tj for tj in self.app.tarjetas if rol in tj.roles), key=lambda tj: tj.orden.get(rol, 99))
        admin = rol == ROL_ADMINISTRADOR
        columnas = 5 if admin else 3
        alto = 258 if admin else 230

        rejilla = tk.Frame(self, bg=t.FONDO)
        rejilla.pack(fill="x", padx=35, pady=(34, 0))
        for c in range(columnas):
            rejilla.columnconfigure(c, weight=1, uniform="tarjeta")
        for i, tj in enumerate(tarjetas):
            f, c = divmod(i, columnas)
            caja = self._tarjeta(rejilla, tj, alto, admin)
            caja.grid(row=f, column=c, sticky="nsew", padx=(0 if c == 0 else 13, 13 if c < columnas - 1 else 0),
                      pady=(0, 26))
        if not tarjetas:
            w.etiqueta(rejilla, "No hay funciones integradas para este rol.", "tenue").grid(row=0, column=0, sticky="w")

        leyenda = tk.Frame(self, bg=t.FONDO)
        leyenda.pack(side="bottom", fill="x", padx=35, pady=(0, 34))
        w.etiqueta(leyenda, "Leyenda", "etiqueta").pack(side="left", padx=(0, 18))
        for texto, estilo in (("Plata: funciones compartidas", "plata"), ("Negro: funciones del empleado", "negro"),
                              ("Rojo: funciones exclusivas del administrador", "rojo")):
            w.Pastilla(leyenda, texto, estilo, alto=30).pack(side="left", padx=(0, 18))

    def _tarjeta(self, padre, tj, alto, admin):
        caja = w.Tarjeta(padre, pad=26 if not admin else 22, modo="xy", height=alto)
        cuerpo = caja.cuerpo
        w.icono(cuerpo, tj.icono, tam=30).pack(anchor="w", pady=(0, 14))
        texto_tipo, estilo = TIPO_FUNCION[tj.tipo]
        w.Pastilla(cuerpo, texto_tipo, estilo).pack(anchor="w", pady=(0, 14))
        w.etiqueta_ajustable(cuerpo, tj.titulo, "titulo_tarjeta", bg=t.BLANCO).pack(fill="x", anchor="w")
        w.etiqueta_ajustable(cuerpo, tj.descripcion, "tenue", bg=t.BLANCO).pack(fill="x", anchor="w", pady=(10, 0))
        if tj.indicador:
            aviso = tj.indicador(self.app)
            if aviso:  # notificación al administrador (p. ej. alertas de stock bajo)
                w.etiqueta(cuerpo, f"● {aviso}", "pastilla", color=t.ROJO, bg=t.BLANCO).pack(anchor="w", pady=(6, 0))

        def abrir(_=None):
            self.app.mostrar(tj.pantalla)

        def resaltar(color):
            caja.resaltar(color)

        for wid in [caja, cuerpo, *cuerpo.winfo_children()]:
            wid.configure(cursor="hand2")
            wid.bind("<Button-1>", abrir)
            wid.bind("<Enter>", lambda e: resaltar(t.ROJO), add="+")
            wid.bind("<Leave>", lambda e: resaltar(t.BORDE), add="+")
        return caja
