"""Pantallas "Generar reportes" y "Estadística de productos más vendidos"."""

from __future__ import annotations

import tkinter as tk

from gamestar.ui import tema as t
from gamestar.ui import widgets as w
from gamestar.ui.app import ROL_ADMINISTRADOR, SOLO_ADMIN, Pantalla, TarjetaMenu


class GenerarReportes(Pantalla):
    """CU-15: elegir el tipo, reunir los datos, registrar quién lo pidió y cuándo, y mostrarlo."""

    titulo = "Generar reportes"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        arriba = w.Tarjeta(self, pad=26)
        arriba.pack(fill="x", padx=35, pady=(34, 26))
        w.etiqueta(arriba.cuerpo, "Tipo de reporte", "etiqueta", bg=t.BLANCO).pack(anchor="w", pady=(0, 8))
        fila = tk.Frame(arriba.cuerpo, bg=t.BLANCO)
        fila.pack(fill="x")
        self.tipo = w.Opciones(fila, [("INVENTARIO", "Inventario"), ("VENTAS", "Ventas"), ("REPARACIONES", "Reparaciones")])
        self.tipo.pack(side="left", fill="x", expand=True)
        w.Boton(fila, "Generar reporte", self.generar, alto=56, ancho=180).pack(side="left", padx=(26, 0))

        vista = w.Tarjeta(self, pad=26, modo="xy")
        vista.pack(fill="both", expand=True, padx=35, pady=(0, 34))
        self.vista = vista.cuerpo
        cab = tk.Frame(self.vista, bg=t.BLANCO)
        cab.pack(fill="x", pady=(0, 18))
        izq = tk.Frame(cab, bg=t.BLANCO)
        izq.pack(side="left")
        self.titulo_vista = w.etiqueta(izq, "Vista del reporte", "seccion", bg=t.BLANCO)
        self.titulo_vista.pack(anchor="w")
        self.subtitulo = w.etiqueta(izq, "Se muestra aquí una vez generado.", "tenue", bg=t.BLANCO)
        self.subtitulo.pack(anchor="w", pady=(4, 0))
        self.solicitado = w.etiqueta(cab, "Solicitado por — · —", "dato", color=t.TEXTO_TENUE, bg=t.BLANCO)
        self.solicitado.pack(side="right", anchor="n")
        self.zona = tk.Frame(self.vista, bg=t.BLANCO)
        self.zona.pack(fill="both", expand=True)
        self._esqueleto()

    def _esqueleto(self):
        """Renglones grises de ejemplo mientras no hay reporte (como en el prototipo)."""
        lienzo = tk.Canvas(self.zona, bg=t.BLANCO, highlightthickness=0, height=300)
        lienzo.pack(fill="x")

        def dibujar(e):
            lienzo.delete("all")
            W = e.width
            cols = (0.01, 0.39, 0.59, 0.80)
            anchos = ((0.15, 0.11, 0.11, 0.11), (0.26, 0.10, 0.10, 0.10), (0.21, 0.13, 0.13, 0.13),
                      (0.17, 0.10, 0.10, 0.10), (0.26, 0.13, 0.13, 0.13), (0.21, 0.10, 0.10, 0.10))
            for r, fila in enumerate(anchos):
                y = 14 + r * 47
                for c, a in zip(cols, fila):
                    w.rect_redondeado(lienzo, c * W, y, (c + a) * W, y + 13, 6,
                                      fill="#C6C8CD" if r == 0 else "#E3E4E7", outline="")
                lienzo.create_line(0, y + 32, W, y + 32, fill=t.BORDE if r == 0 else t.SEPARADOR, width=2 if r == 0 else 1)

        lienzo.bind("<Configure>", dibujar)

    def generar(self):
        tipo = self.tipo.valor()
        if not tipo:
            self.app.aviso("Elige el tipo de reporte: inventario, ventas o reparaciones.")
            return
        r = self.llamar("reportes.generar", tipo=tipo)
        if not r:
            return
        nombres = {"INVENTARIO": "inventario", "VENTAS": "ventas", "REPARACIONES": "reparaciones"}
        self.titulo_vista.configure(text=f"Reporte de {nombres[r['tipo']]}")
        self.subtitulo.configure(text=r["aviso"] or f"Reporte n.º {r['idReporte']} · {len(r['filas'])} registros.")
        self.solicitado.configure(text=f"Solicitado por {r['solicitadoPor']} · {r['fechaGeneracion']}")
        for hijo in self.zona.winfo_children():
            hijo.destroy()
        w.resumen(self.zona, r["resumen"]).pack(fill="x", pady=(0, 18))
        pesos = {"Folio": 7, "Fecha": 18, "Ingreso": 18, "Entrega": 12, "Producto": 24, "Cliente": 16, "Equipo": 16}
        tabla = w.Tabla(self.zona, [(c, pesos.get(c, 12)) for c in r["columnas"]],
                        vacio=r["aviso"] or "Sin registros.")
        tabla.pack(fill="both", expand=True)
        tabla.cargar(r["filas"])


class ProductosMasVendidos(Pantalla):
    """Resultado 5 de la evaluación del prototipo: ranking por unidades vendidas."""

    titulo = "Estadística de productos más vendidos"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        tarjeta = w.Tarjeta(self, pad=26, modo="xy")
        tarjeta.pack(fill="both", expand=True, padx=35, pady=(34, 34))
        c = tarjeta.cuerpo
        w.titulo_tarjeta(c, "Productos más vendidos",
                         "Ordenados de mayor a menor número de unidades vendidas, a partir del historial de ventas.",
                         pady=(0, 22))
        datos = self.llamar("reportes.mas_vendidos", limite=10)
        if not datos:
            w.etiqueta(c, "Todavía no hay ventas registradas.", "tenue", bg=t.BLANCO).pack(anchor="w")
            return
        lista = w.Desplazable(c, bg=t.BLANCO)
        lista.pack(fill="both", expand=True)
        maximo = max(d["unidades"] for d in datos) or 1
        for n, d in enumerate(datos, start=1):
            self._fila(lista.interior, n, d, d["unidades"] / maximo)

    def _fila(self, padre, n, d, proporcion):
        fila = tk.Frame(padre, bg=t.BLANCO)
        fila.pack(fill="x", pady=(0, 17))
        fila.columnconfigure(2, weight=1)
        fila.columnconfigure(1, minsize=330)
        num = tk.Canvas(fila, width=40, height=40, bg=t.BLANCO, highlightthickness=0)
        num.create_oval(1, 1, 39, 39, fill=t.NEGRO, outline=t.NEGRO)
        num.create_text(20, 20, text=str(n), fill=t.BLANCO, font=t.fuente("numero"))
        num.grid(row=0, column=0, padx=(0, 26))
        nombre = tk.Frame(fila, bg=t.BLANCO, width=320)
        nombre.grid(row=0, column=1, sticky="w")
        w.etiqueta(nombre, d["nombre"], "cuerpo_negrita", color="#3F4147", bg=t.BLANCO, wraplength=320).pack(anchor="w")
        w.etiqueta(nombre, d["categoria"], "tenue", bg=t.BLANCO).pack(anchor="w")
        barra = tk.Canvas(fila, height=26, bg=t.BLANCO, highlightthickness=0)
        barra.grid(row=0, column=2, sticky="ew", padx=(20, 60))

        def dibujar(e, p=proporcion):
            barra.delete("all")
            w.rect_redondeado(barra, 0, 0, e.width - 1, 25, 12.5, fill=t.BARRA_VACIA, outline="")
            w.rect_redondeado(barra, 0, 0, max(26, (e.width - 1) * p), 25, 12.5, fill=t.ROJO, outline="")

        barra.bind("<Configure>", dibujar)
        w.etiqueta(fila, f"{d['unidades']} {'ud.' if d['unidades'] == 1 else 'uds.'}", "cuerpo_negrita", color="#3F4147", bg=t.BLANCO, width=9,
                   anchor="e").grid(row=0, column=3)


def registrar(app):
    app.registrar_pantalla("reportes", GenerarReportes)
    app.registrar_pantalla("mas_vendidos", ProductosMasVendidos)
    app.registrar_tarjeta(TarjetaMenu("reportes", "Generar reportes", "Inventario / ventas / reparaciones", "barras",
                                      (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 6}))
    app.registrar_tarjeta(TarjetaMenu("mas_vendidos", "Estadística de productos más vendidos",
                                      "Ranking de productos por unidades vendidas", "estrella",
                                      (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 7}))
