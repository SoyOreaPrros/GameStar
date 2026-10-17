"""Componentes visuales reutilizables que reproducen el prototipo final:
tarjetas redondeadas, botones, pastillas, campos con borde, tablas e íconos."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from . import tema as t


def _bg(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return t.FONDO


def rect_redondeado(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    puntos = []
    for cx, cy, a0 in ((x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0), (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
        for paso in range(0, 91, 10):
            a = math.radians(a0 + paso)
            puntos += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return canvas.create_polygon(puntos, **kw)


# ---------------------------------------------------------------------------
# Contenedores
# ---------------------------------------------------------------------------
class Tarjeta(tk.Canvas):
    """Tarjeta blanca de esquinas redondeadas.

    modo="x": el ancho lo da el contenedor y el alto el contenido.
    modo="xy": ancho y alto los da el contenedor (pack/grid con expand).
    modo="contenido": el tamaño lo dicta el contenido.
    """

    def __init__(self, padre, pad=24, radio=14, modo="x", relleno=t.BLANCO, borde=t.BORDE, padx=None, pady=None, **kw):
        super().__init__(padre, bg=_bg(padre), highlightthickness=0, bd=0, **kw)
        self.padx = pad if padx is None else padx
        self.pady = pad if pady is None else pady
        self.radio, self.modo, self.relleno, self.borde = radio, modo, relleno, borde
        self.cuerpo = tk.Frame(self, bg=relleno)
        self._ventana = self.create_window(self.padx, self.pady, window=self.cuerpo, anchor="nw")
        self.bind("<Configure>", self._redibujar)
        if modo != "xy":
            self.cuerpo.bind("<Configure>", self._ajustar, add="+")

    def _ajustar(self, _=None):
        alto = self.cuerpo.winfo_reqheight() + 2 * self.pady
        if self.winfo_reqheight() != alto:
            self.configure(height=alto)
        if self.modo == "contenido":
            ancho = self.cuerpo.winfo_reqwidth() + 2 * self.padx
            if self.winfo_reqwidth() != ancho:
                self.configure(width=ancho)

    def _redibujar(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        self.delete("fondo")
        rect_redondeado(self, 0.5, 0.5, w - 1.5, h - 1.5, self.radio, fill=self.relleno, outline=self.borde, tags="fondo")
        self.tag_lower("fondo")
        if self.modo in ("x", "xy"):
            self.itemconfigure(self._ventana, width=max(1, w - 2 * self.padx))
        if self.modo == "xy":
            self.itemconfigure(self._ventana, height=max(1, h - 2 * self.pady))

    def resaltar(self, color):
        self.borde = color
        self._redibujar()


class Desplazable(tk.Frame):
    """Marco con barra de desplazamiento vertical; el contenido va en ``.interior``."""

    def __init__(self, padre, bg=None, **kw):
        bg = bg or _bg(padre)
        super().__init__(padre, bg=bg, **kw)
        self.lienzo = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.interior = tk.Frame(self.lienzo, bg=bg)
        self._v = self.lienzo.create_window(0, 0, window=self.interior, anchor="nw")
        self.lienzo.configure(yscrollcommand=self._mover_barra)
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.interior.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._v, width=e.width))

    def _mover_barra(self, inicio, fin):
        if float(inicio) <= 0 and float(fin) >= 1:
            if self.barra.winfo_ismapped():
                self.barra.pack_forget()
        elif not self.barra.winfo_ismapped():
            self.barra.pack(side="right", fill="y", before=self.lienzo)
        self.barra.set(inicio, fin)

    def desplazar(self, paso):
        if self.barra.winfo_ismapped():
            self.lienzo.yview_scroll(paso * 2, "units")

    def arriba(self):
        self.lienzo.yview_moveto(0)


def instalar_rueda(raiz: tk.Tk):
    """Un solo manejador de la rueda del ratón para todos los marcos desplazables."""

    def rueda(e):
        try:
            w = raiz.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):
            return
        while w is not None and not isinstance(w, Desplazable):
            w = getattr(w, "master", None)
        if w is not None:
            w.desplazar(-1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1)

    for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        raiz.bind_all(evento, rueda)


# ---------------------------------------------------------------------------
# Texto, botones y pastillas
# ---------------------------------------------------------------------------
def etiqueta(padre, texto="", estilo="cuerpo", color=None, **kw):
    colores = {"tenue": t.TEXTO_TENUE, "caps": t.TEXTO_CAPS}
    return tk.Label(padre, text=texto, font=t.fuente(estilo), fg=color or colores.get(estilo, t.TEXTO),
                    bg=kw.pop("bg", _bg(padre)), anchor=kw.pop("anchor", "w"), justify=kw.pop("justify", "left"), **kw)


def etiqueta_ajustable(padre, texto="", estilo="cuerpo", color=None, **kw):
    """Etiqueta que hace salto de línea al ancho disponible."""
    lbl = etiqueta(padre, texto, estilo, color, width=1, **kw)
    lbl.bind("<Configure>", lambda e: lbl.configure(wraplength=max(20, e.width - 4)))
    return lbl


class Boton(tk.Canvas):
    ESTILOS = {
        # estilo: (relleno, borde, texto, relleno_hover)
        "primario": (t.ROJO, t.ROJO, t.BLANCO, t.ROJO_OSCURO),
        "secundario": (t.BLANCO, t.ROJO, t.ROJO, "#FDF1F1"),
    }

    def __init__(self, padre, texto, comando=None, estilo="primario", alto=46, ancho=None, radio=8):
        f = t.fuente("boton")
        ancho = ancho or f.measure(texto) + 52
        super().__init__(padre, width=ancho, height=alto, bg=_bg(padre), highlightthickness=0, bd=0, cursor="hand2")
        self.texto, self.comando, self.estilo, self.radio = texto, comando, estilo, radio
        self.habilitado = True
        self._hover = False
        self.bind("<Configure>", lambda e: self._dibujar())
        self.bind("<Enter>", lambda e: self._cambiar_hover(True))
        self.bind("<Leave>", lambda e: self._cambiar_hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        self._dibujar()

    def _cambiar_hover(self, valor):
        self._hover = valor
        self._dibujar()

    def _dibujar(self):
        self.delete("all")
        relleno, borde, color, hover = self.ESTILOS[self.estilo]
        if self._hover and self.habilitado:
            relleno = hover
        if not self.habilitado:
            relleno, borde, color = ("#E2A3A4", "#E2A3A4", t.BLANCO) if self.estilo == "primario" else (t.BLANCO, "#E2A3A4", "#E2A3A4")
        w, h = self.winfo_width() or int(self.cget("width")), self.winfo_height() or int(self.cget("height"))
        rect_redondeado(self, 1, 1, w - 2, h - 2, self.radio, fill=relleno, outline=borde, width=1.5)
        self.create_text(w / 2, h / 2, text=self.texto, fill=color, font=t.fuente("boton"))

    def _click(self, e):
        if self.habilitado and self.comando and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.comando()

    def habilitar(self, valor: bool):
        self.habilitado = valor
        self.configure(cursor="hand2" if valor else "arrow")
        self._dibujar()


def enlace(padre, texto, comando, estilo="enlace", color=t.ROJO, **kw):
    lbl = tk.Label(padre, text=texto, font=t.fuente(estilo), fg=color, bg=kw.pop("bg", _bg(padre)), cursor="hand2", **kw)
    lbl.bind("<Button-1>", lambda e: comando())
    lbl.bind("<Enter>", lambda e: lbl.configure(fg=t.ROJO_OSCURO))
    lbl.bind("<Leave>", lambda e: lbl.configure(fg=color))
    return lbl


class Pastilla(tk.Canvas):
    def __init__(self, padre, texto, estilo="plata", alto=30, fuente="pastilla"):
        f = t.fuente(fuente)
        ancho = f.measure(texto) + 28
        super().__init__(padre, width=ancho, height=alto, bg=_bg(padre), highlightthickness=0, bd=0)
        relleno, borde, color = t.ESTILOS_PASTILLA[estilo]
        rect_redondeado(self, 1, 1, ancho - 2, alto - 2, alto / 2, fill=relleno, outline=borde)
        self.create_text(ancho / 2, alto / 2, text=texto, fill=color, font=f)


# ---------------------------------------------------------------------------
# Campos de captura
# ---------------------------------------------------------------------------
class Campo(tk.Frame):
    """Campo de texto con borde redondeado visual, marcador de ejemplo y foco rojo."""

    def __init__(self, padre, marcador="", oculto=False, ancho=None, alto=46, justificar="left", valor=""):
        super().__init__(padre, bg=_bg(padre))
        self.lienzo = tk.Canvas(self, height=alto, bg=_bg(padre), highlightthickness=0, bd=0)
        if ancho:
            self.lienzo.configure(width=ancho)
        self.lienzo.pack(fill="x", expand=True)
        self.marcador, self.oculto = marcador, oculto
        self._con_marcador = False
        self.entrada = tk.Entry(self.lienzo, relief="flat", bd=0, highlightthickness=0, bg=t.BLANCO, fg=t.TEXTO,
                                insertbackground=t.TEXTO, font=t.fuente("dato"), justify=justificar)
        self._v = self.lienzo.create_window(14, alto / 2, window=self.entrada, anchor="w")
        self._foco = False
        self.lienzo.bind("<Configure>", lambda e: self._dibujar())
        self.lienzo.bind("<Button-1>", lambda e: self.entrada.focus_set())
        self.entrada.bind("<FocusIn>", self._entrar, add="+")
        self.entrada.bind("<FocusOut>", self._salir, add="+")
        if valor != "":
            self.fijar(valor)
        else:
            self._poner_marcador()

    def _dibujar(self):
        w, h = self.lienzo.winfo_width(), self.lienzo.winfo_height()
        self.lienzo.delete("marco")
        rect_redondeado(self.lienzo, 1, 1, w - 2, h - 2, 8, fill=t.BLANCO,
                        outline=t.ROJO if self._foco else t.BORDE_CAMPO, width=1.5 if self._foco else 1, tags="marco")
        self.lienzo.tag_lower("marco")
        self.lienzo.itemconfigure(self._v, width=max(10, w - 28))

    def _poner_marcador(self):
        if not self.entrada.get() and self.marcador:
            self._con_marcador = True
            self.entrada.configure(show="", fg=t.MARCADOR)
            self.entrada.insert(0, self.marcador)

    def _quitar_marcador(self):
        if self._con_marcador:
            self._con_marcador = False
            self.entrada.delete(0, "end")
            self.entrada.configure(fg=t.TEXTO, show="•" if self.oculto else "")

    def _entrar(self, _):
        self._foco = True
        self._quitar_marcador()
        self._dibujar()

    def _salir(self, _):
        self._foco = False
        self._poner_marcador()
        self._dibujar()

    def valor(self) -> str:
        return "" if self._con_marcador else self.entrada.get()

    def fijar(self, valor):
        self._quitar_marcador()
        self.entrada.configure(fg=t.TEXTO, show="•" if self.oculto else "")
        self.entrada.delete(0, "end")
        self.entrada.insert(0, str(valor))
        if self.focus_get() is not self.entrada:
            self._poner_marcador()

    def limpiar(self):
        self.entrada.delete(0, "end")
        self._con_marcador = False
        if self.focus_get() is not self.entrada:
            self._poner_marcador()

    def al_escribir(self, funcion):
        self.entrada.bind("<KeyRelease>", lambda e: funcion(), add="+")

    def al_enter(self, funcion):
        self.entrada.bind("<Return>", lambda e: funcion(), add="+")

    def enfocar(self):
        self.entrada.focus_set()


class AreaTexto(tk.Frame):
    def __init__(self, padre, marcador="", alto=6):
        super().__init__(padre, bg=t.BLANCO, highlightthickness=1, highlightbackground=t.BORDE_CAMPO, highlightcolor=t.ROJO)
        self.texto = tk.Text(self, height=alto, relief="flat", bd=0, wrap="word", font=t.fuente("dato"), fg=t.TEXTO,
                             bg=t.BLANCO, insertbackground=t.TEXTO, padx=12, pady=10, highlightthickness=0)
        self.texto.pack(fill="both", expand=True)
        self.marcador = marcador
        self._con_marcador = False
        self.texto.bind("<FocusIn>", lambda e: (self.configure(highlightbackground=t.ROJO), self._quitar()))
        self.texto.bind("<FocusOut>", lambda e: (self.configure(highlightbackground=t.BORDE_CAMPO), self._poner()))
        self._poner()

    def _poner(self):
        if not self.texto.get("1.0", "end").strip() and self.marcador:
            self._con_marcador = True
            self.texto.delete("1.0", "end")
            self.texto.insert("1.0", self.marcador)
            self.texto.configure(fg=t.MARCADOR)

    def _quitar(self):
        if self._con_marcador:
            self._con_marcador = False
            self.texto.delete("1.0", "end")
            self.texto.configure(fg=t.TEXTO)

    def valor(self) -> str:
        return "" if self._con_marcador else self.texto.get("1.0", "end").strip()

    def limpiar(self):
        self.texto.delete("1.0", "end")
        self._con_marcador = False
        self._poner()


def configurar_estilos(raiz: tk.Tk):
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    estilo.configure("GS.TCombobox", fieldbackground=t.BLANCO, background=t.BLANCO, foreground=t.TEXTO,
                     bordercolor=t.BORDE_CAMPO, lightcolor=t.BLANCO, darkcolor=t.BLANCO, arrowcolor=t.TEXTO,
                     padding=(12, 9, 8, 9), arrowsize=14)
    estilo.map("GS.TCombobox", fieldbackground=[("readonly", t.BLANCO)], bordercolor=[("focus", t.ROJO)],
               selectbackground=[("readonly", t.BLANCO)], selectforeground=[("readonly", t.TEXTO)])
    estilo.configure("Vertical.TScrollbar", background=t.PLATA, troughcolor=t.FONDO, bordercolor=t.FONDO,
                     arrowcolor=t.TEXTO_TENUE, lightcolor=t.PLATA, darkcolor=t.PLATA)
    raiz.option_add("*TCombobox*Listbox.font", t.fuente("cuerpo"))
    raiz.option_add("*TCombobox*Listbox.selectBackground", t.ROJO_SUAVE)
    raiz.option_add("*TCombobox*Listbox.selectForeground", t.TEXTO)


class Selector(ttk.Combobox):
    """Lista desplegable. ``opciones`` es una lista de (valor, texto)."""

    def __init__(self, padre, opciones=(), editable=False, **kw):
        super().__init__(padre, style="GS.TCombobox", state="normal" if editable else "readonly",
                         font=t.fuente("dato"), **kw)
        self.fijar_opciones(opciones)

    def fijar_opciones(self, opciones):
        self._opciones = list(opciones)
        self.configure(values=[txt for _, txt in self._opciones])

    def seleccionar(self, valor):
        for i, (v, _) in enumerate(self._opciones):
            if v == valor:
                self.current(i)
                return

    def valor(self):
        texto = self.get()
        for v, txt in self._opciones:
            if txt == texto:
                return v
        return None


class Opciones(tk.Frame):
    """Grupo de opciones excluyentes con recuadro (como "Nuevo estado" o "Tipo de reporte")."""

    def __init__(self, padre, opciones, al_cambiar=None, columnas=None):
        super().__init__(padre, bg=_bg(padre))
        self.variable = tk.StringVar(value="")
        self._cajas = {}
        self.al_cambiar = al_cambiar
        for i, (valor, texto) in enumerate(opciones):
            caja = tk.Frame(self, bg=t.BLANCO, highlightthickness=1, highlightbackground=t.BORDE_CAMPO, cursor="hand2")
            caja.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 9, 0))
            self.columnconfigure(i, weight=1, uniform="op")
            rb = tk.Radiobutton(caja, text=texto, value=valor, variable=self.variable, font=t.fuente("dato"),
                                bg=t.BLANCO, activebackground=t.BLANCO, fg=t.TEXTO, selectcolor=t.BLANCO,
                                highlightthickness=0, bd=0, anchor="w", padx=14, pady=14, cursor="hand2",
                                command=self._cambio)
            rb.pack(fill="x")
            caja.bind("<Button-1>", lambda e, v=valor: (self.variable.set(v), self._cambio()))
            self._cajas[valor] = caja

    def _cambio(self):
        for v, caja in self._cajas.items():
            caja.configure(highlightbackground=t.ROJO if v == self.variable.get() else t.BORDE_CAMPO)
        if self.al_cambiar:
            self.al_cambiar(self.variable.get())

    def valor(self):
        return self.variable.get() or None

    def fijar(self, valor):
        self.variable.set(valor or "")
        self._cambio()


def campo_con_titulo(padre, titulo, widget_factory, pady=(0, 16)):
    """Etiqueta en negrita sobre un campo, como en todos los formularios del diseño."""
    marco = tk.Frame(padre, bg=_bg(padre))
    etiqueta(marco, titulo, "etiqueta").pack(anchor="w", pady=(0, 7))
    w = widget_factory(marco)
    w.pack(fill="x")
    marco.pack(fill="x", pady=pady)
    return w


def titulo_tarjeta(cuerpo, titulo, subtitulo=None, pady=(0, 18)):
    marco = tk.Frame(cuerpo, bg=_bg(cuerpo))
    marco.pack(fill="x", pady=pady)
    etiqueta(marco, titulo, "seccion").pack(anchor="w")
    sub = None
    if subtitulo is not None:
        sub = etiqueta(marco, subtitulo, "tenue")
        sub.pack(anchor="w", pady=(4, 0))
    marco.subtitulo = sub
    return marco


def columnas_tarjetas(padre, pesos, modo="xy", pad=26, separacion=26, margen=(35, 26, 35, 34)):
    """Distribuye tarjetas blancas en columnas que ocupan toda la pantalla."""
    izq, arr, der, aba = margen
    fila = tk.Frame(padre, bg=_bg(padre))
    fila.pack(fill="both", expand=True, padx=(izq, der), pady=(arr, aba))
    cuerpos = []
    for i, peso in enumerate(pesos):
        fila.columnconfigure(i, weight=peso, uniform="tarjetas")
        tj = Tarjeta(fila, pad=pad, modo=modo)
        tj.grid(row=0, column=i, sticky="nsew" if modo == "xy" else "new", padx=(0 if i == 0 else separacion, 0))
        cuerpos.append(tj.cuerpo)
    fila.rowconfigure(0, weight=1)
    return cuerpos


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------
class Tabla(tk.Frame):
    """Tabla con encabezados en mayúsculas y renglones separados por líneas finas.

    ``columnas``: lista de (título, peso). Cada celda de ``cargar`` puede ser texto o
    una función que recibe el contenedor y regresa un widget.
    """

    def __init__(self, padre, columnas, desplazable=True, al_seleccionar=None, alto_fila=12, vacio="Sin registros."):
        bg = _bg(padre)
        super().__init__(padre, bg=bg)
        self.columnas, self.al_seleccionar, self.alto_fila, self.vacio = columnas, al_seleccionar, alto_fila, vacio
        self.seleccion = None
        self._filas: list[tk.Frame] = []
        enc = tk.Frame(self, bg=bg)
        enc.pack(fill="x")
        self._columnas(enc)
        for i, (titulo, _) in enumerate(columnas):
            etiqueta_ajustable(enc, titulo.upper(), "caps").grid(row=0, column=i, sticky="ew", padx=13, pady=(4, 12))
        tk.Frame(self, bg=t.BORDE, height=2).pack(fill="x")
        if desplazable:
            self.marco = Desplazable(self, bg=bg)
            self.marco.pack(fill="both", expand=True)
            self.cuerpo = self.marco.interior
            self._enc = enc
            self.marco.barra.bind("<Map>", lambda e: enc.pack_configure(padx=(0, self.marco.barra.winfo_width())))
            self.marco.barra.bind("<Unmap>", lambda e: enc.pack_configure(padx=0))
        else:
            self.marco = None
            self.cuerpo = tk.Frame(self, bg=bg)
            self.cuerpo.pack(fill="both", expand=True)

    def _columnas(self, marco):
        for i, (_, peso) in enumerate(self.columnas):
            marco.columnconfigure(i, weight=peso, uniform="col")

    def cargar(self, filas, datos=None):
        for w in self.cuerpo.winfo_children():
            w.destroy()
        self._filas, self._datos, self.seleccion = [], list(datos or filas), None
        bg = _bg(self)
        if not filas:
            etiqueta(self.cuerpo, self.vacio, "tenue").pack(anchor="w", padx=13, pady=16)
            return
        for n, celdas in enumerate(filas):
            fila = tk.Frame(self.cuerpo, bg=bg)
            fila.pack(fill="x")
            self._columnas(fila)
            for i, celda in enumerate(celdas):
                if callable(celda):
                    w = celda(fila)
                    w.grid(row=0, column=i, sticky="w", padx=13, pady=self.alto_fila - 4)
                else:
                    w = etiqueta_ajustable(fila, "" if celda is None else str(celda), "cuerpo")
                    w.grid(row=0, column=i, sticky="ew", padx=13, pady=self.alto_fila)
            tk.Frame(self.cuerpo, bg=t.SEPARADOR, height=1).pack(fill="x")
            self._filas.append(fila)
            if self.al_seleccionar:
                for w in [fila, *fila.winfo_children()]:
                    if isinstance(w, tk.Label) and w.cget("cursor") == "hand2":
                        continue
                    w.bind("<Button-1>", lambda e, k=n: self.seleccionar(k), add="+")
        if self.marco:
            self.marco.arriba()

    def seleccionar(self, n, avisar=True):
        bg = _bg(self)
        for k, fila in enumerate(self._filas):
            color = t.FILA_SELECCION if k == n else bg
            fila.configure(bg=color)
            for w in fila.winfo_children():
                if isinstance(w, (tk.Label, tk.Frame)) and not isinstance(w, tk.Canvas):
                    w.configure(bg=color)
        self.seleccion = n
        if avisar and self.al_seleccionar and n is not None and n < len(self._datos):
            self.al_seleccionar(self._datos[n])


def resumen(padre, pares, columnas=None):
    """Bloque gris con pares DATO / valor (p. ej. FECHA, USUARIO, SUCURSAL, TOTAL)."""
    caja = Tarjeta(padre, padx=18, pady=16, radio=10, relleno=t.FONDO, borde=t.FONDO)
    columnas = columnas or len(pares)
    valores = {}
    for i, (titulo, valor) in enumerate(pares):
        f, c = divmod(i, columnas)
        celda = tk.Frame(caja.cuerpo, bg=t.FONDO)
        celda.grid(row=f, column=c, sticky="new", pady=(0 if f == 0 else 14, 0))
        caja.cuerpo.columnconfigure(c, weight=1, uniform="r")
        etiqueta(celda, titulo.upper(), "caps", bg=t.FONDO).pack(anchor="w")
        lbl = etiqueta_ajustable(celda, valor, "dato", color=t.TEXTO_TENUE, bg=t.FONDO)
        lbl.pack(fill="x", anchor="w", pady=(3, 0))
        valores[titulo] = lbl
    caja.valores = valores
    return caja


# ---------------------------------------------------------------------------
# Íconos dibujados (trazo rojo, estilo de línea como en el prototipo)
# ---------------------------------------------------------------------------
def icono(padre, nombre, tam=30, color=t.ROJO, grosor=None):
    c = tk.Canvas(padre, width=tam, height=tam, bg=_bg(padre), highlightthickness=0, bd=0)
    k = tam / 24
    g = grosor or max(1.5, 1.8 * k)

    def P(*pts):
        return [v * k for v in pts]

    def linea(*pts, **kw):
        c.create_line(*P(*pts), fill=color, width=g, capstyle="round", joinstyle="round", **kw)

    def circulo(cx, cy, r, relleno=""):
        c.create_oval(*P(cx - r, cy - r, cx + r, cy + r), outline=color, width=g, fill=relleno)

    if nombre == "caja":
        linea(12, 2.5, 20.5, 7, 20.5, 17, 12, 21.5, 3.5, 17, 3.5, 7, 12, 2.5)
        linea(3.5, 7, 12, 11.5, 20.5, 7)
        linea(12, 11.5, 12, 21.5)
    elif nombre == "carrito":
        linea(2, 3, 5, 3, 7.5, 15, 18.5, 15, 21, 7, 6, 7)
        circulo(9, 19.5, 1.6)
        circulo(17.5, 19.5, 1.6)
    elif nombre == "llave":
        # llave española: mango diagonal y boca abierta hacia arriba a la derecha
        c.create_arc(*P(10.5, 3.5, 20.5, 13.5), start=80, extent=290, style="arc", outline=color, width=g)
        linea(4, 20, 12, 12)
        linea(4, 20, 5.5, 21.5, 13.4, 13.6)
    elif nombre == "lista":
        linea(4, 6, 20, 6)
        linea(4, 12, 16, 12)
        linea(4, 18, 18, 18)
    elif nombre == "usuario":
        circulo(12, 8, 4)
        c.create_arc(*P(4.5, 14, 19.5, 29), start=0, extent=180, style="arc", outline=color, width=g)
    elif nombre == "reloj":
        circulo(12, 12, 9)
        linea(12, 7, 12, 12, 15.5, 14)
    elif nombre == "barras":
        linea(5, 20, 5, 12)
        linea(12, 20, 12, 5)
        linea(19, 20, 19, 14)
    elif nombre == "estrella":
        pts = []
        for i in range(10):
            r = 9.5 if i % 2 == 0 else 4
            a = math.radians(-90 + i * 36)
            pts += [12 + r * math.cos(a), 12.8 + r * math.sin(a)]
        c.create_polygon(*P(*pts), outline=color, fill="", width=g, joinstyle="round")
    elif nombre == "alerta":
        c.create_polygon(*P(12, 3, 22, 20.5, 2, 20.5), outline=color, fill="", width=g, joinstyle="round")
        linea(12, 9.5, 12, 14)
        circulo(12, 17.2, 0.4, relleno=color)
    elif nombre == "flechas":
        linea(4, 8, 20, 8)
        linea(16, 4, 20, 8, 16, 12)
        linea(20, 16, 4, 16)
        linea(8, 12, 4, 16, 8, 20)
    elif nombre == "atras":
        linea(15, 5, 8, 12, 15, 19)
    elif nombre == "error":
        circulo(12, 12, 9.5)
        linea(12, 7, 12, 13)
        circulo(12, 16.5, 0.4, relleno=color)
    return c
