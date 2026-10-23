"""Pantallas de reparaciones.

Empleado: flujo de cuatro pasos consecutivos del diagrama de navegación (registrar la
reparación, actualizar su estado, registrar las refacciones usadas y registrar la
entrega del equipo). Administrador: consultar reparaciones (CU-14).
"""

from __future__ import annotations

import tkinter as tk
from datetime import date

from gamestar.nucleo.reglas import NOMBRE_ESTADO
from gamestar.ui import tema as t
from gamestar.ui import widgets as w
from gamestar.ui.app import DEL_EMPLEADO, ROL_ADMINISTRADOR, ROL_EMPLEADO, SOLO_ADMIN, Pantalla, TarjetaMenu

PASOS = (("rep_registrar", "Registrar reparación"), ("rep_estado", "Actualizar estado"),
         ("rep_refacciones", "Registrar refacciones usadas"), ("rep_entrega", "Registrar entrega del equipo"))


class PasoReparacion(Pantalla):
    paso = 1
    roles = (ROL_EMPLEADO,)

    @property
    def titulo(self):
        return PASOS[self.paso - 1][1]

    def construir(self):
        barra = tk.Frame(self, bg=t.FONDO)
        barra.pack(fill="x", padx=35, pady=(34, 26))
        for i, (clave, nombre) in enumerate(PASOS, start=1):
            barra.columnconfigure(i - 1, weight=1, uniform="paso")
            activo = i == self.paso
            caja = w.Tarjeta(barra, padx=16, pady=12, radio=8, relleno=t.ROJO_SUAVE if activo else t.BLANCO,
                             borde=t.ROJO if activo else t.BORDE)
            caja.grid(row=0, column=i - 1, sticky="ew", padx=(0 if i == 1 else 10, 0))
            fondo = t.ROJO_SUAVE if activo else t.BLANCO
            num = tk.Canvas(caja.cuerpo, width=26, height=26, bg=fondo, highlightthickness=0)
            num.create_oval(1, 1, 25, 25, fill=t.ROJO if activo else t.PLATA, outline="")
            num.create_text(13, 13, text=str(i), fill=t.BLANCO if activo else t.TEXTO, font=t.fuente("pastilla"))
            num.pack(side="left", padx=(0, 12))
            lbl = w.etiqueta(caja.cuerpo, nombre, "cuerpo_negrita" if activo else "cuerpo", bg=fondo,
                             color=t.TEXTO if activo else t.TEXTO_TENUE)
            lbl.pack(side="left")
            for wid in (caja, caja.cuerpo, num, lbl):
                wid.configure(cursor="hand2")
                wid.bind("<Button-1>", lambda e, c=clave: self.app.mostrar(c))
        tarjeta = w.Tarjeta(self, pad=26, modo="xy")
        tarjeta.pack(fill="both", expand=True, padx=35, pady=(0, 34))
        self.cuerpo = tarjeta.cuerpo
        self.botones = tk.Frame(self.cuerpo, bg=t.BLANCO)
        self.botones.pack(side="bottom", fill="x")
        self.contenido()

    def contenido(self):
        pass

    # Reparación con la que se trabaja a lo largo de los pasos.
    @property
    def actual(self):
        return self.app.estado.get("reparacion")

    @actual.setter
    def actual(self, r):
        self.app.estado["reparacion"] = r


class Localizador(tk.Frame):
    """Campo "Localizar la reparación" con resultados por folio, cliente, teléfono o equipo, y
    el bloque con cliente, equipo y estado de la reparación elegida."""

    def __init__(self, padre, app, al_elegir, titulo_estado="Estado actual"):
        super().__init__(padre, bg=t.BLANCO)
        self.app, self.al_elegir = app, al_elegir
        self.campo = w.campo_con_titulo(self, "Localizar la reparación",
                                        lambda m: w.Campo(m, "Buscar reparación por folio, cliente, teléfono o equipo"),
                                        pady=(0, 6))
        self.resultados = tk.Frame(self, bg=t.BLANCO, highlightthickness=1, highlightbackground=t.BORDE)
        self.res = w.resumen(self, [("Cliente", "[Nombre del cliente]"), ("Equipo", "[Equipo]"), (titulo_estado, "[Estado]")])
        self.res.pack(fill="x", pady=(16, 0))
        self.campo.al_escribir(self._programar)
        self.campo.entrada.bind("<FocusIn>", lambda e: self._programar(), add="+")
        self._pendiente = None

    def _programar(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(200, self._buscar)

    def _buscar(self):
        self._pendiente = None
        datos = self.app.llamar("reparaciones.buscar", texto=self.campo.valor(), limite=6)
        for h in self.resultados.winfo_children():
            h.destroy()
        if not datos:
            self.resultados.pack_forget()
            if datos is not None and self.campo.valor():
                w.etiqueta(self.resultados, "Sin coincidencias.", "tenue", bg=t.BLANCO).pack(anchor="w", padx=14, pady=8)
                self.resultados.pack(fill="x", before=self.res)
            return
        for r in datos:
            texto = f"#{r['idReparacion']}  ·  {r['cliente']}  ·  {r['telefono']}  ·  {r['equipo']}  ·  {r['nombreEstado']}"
            fila = w.etiqueta(self.resultados, texto, "cuerpo", bg=t.BLANCO, cursor="hand2", padx=14, pady=7)
            fila.pack(fill="x")
            fila.bind("<Enter>", lambda e, f=fila: f.configure(bg=t.FILA_SELECCION))
            fila.bind("<Leave>", lambda e, f=fila: f.configure(bg=t.BLANCO))
            fila.bind("<Button-1>", lambda e, r=r: self.elegir(r))
        self.resultados.pack(fill="x", before=self.res)

    def elegir(self, r, avisar=True):
        self.resultados.pack_forget()
        self.campo.fijar(f"#{r['idReparacion']} · {r['cliente']}")
        self.mostrar(r)
        if avisar:
            self.al_elegir(r)

    def mostrar(self, r):
        valores = list(self.res.valores.values())
        valores[0].configure(text=f"{r['cliente']}  ·  {r['telefono']}")
        valores[1].configure(text=r["equipo"])
        texto = r["nombreEstado"]
        if r.get("fechaEntrega"):
            texto += f" · entregada el {r['fechaEntrega']}"
        valores[2].configure(text=texto)


class RegistrarReparacion(PasoReparacion):
    """Paso 1 · CU-04."""

    paso = 1

    def contenido(self):
        c = self.cuerpo
        w.titulo_tarjeta(c, "Datos del cliente y equipo", "Captura los datos del cliente, del equipo recibido y la falla reportada.")
        fila = tk.Frame(c, bg=t.BLANCO)
        fila.pack(fill="x")
        cajas = []
        for i in range(3):
            fila.columnconfigure(i, weight=1, uniform="c")
            caja = tk.Frame(fila, bg=t.BLANCO)
            caja.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 11, 11 if i < 2 else 0))
            cajas.append(caja)
        self.cliente = w.campo_con_titulo(cajas[0], "Datos del cliente", lambda m: w.Campo(m, "Nombre del cliente"))
        self.telefono = w.campo_con_titulo(cajas[1], "Teléfono de contacto del cliente", lambda m: w.Campo(m, "Número telefónico"))
        self.equipo = w.campo_con_titulo(cajas[2], "Datos del equipo recibido", lambda m: w.Campo(m, "Equipo"))
        self.falla = w.campo_con_titulo(c, "Diagnóstico o falla reportada", lambda m: w.AreaTexto(m, "Diagnóstico o falla reportada", alto=6))
        nota = tk.Frame(c, bg=t.BLANCO)
        nota.pack(fill="x", pady=(6, 0))
        w.Pastilla(nota, "Estado inicial: Pendiente", "amarillo", alto=32).pack(side="left")
        w.etiqueta(nota, "La fecha de ingreso se asigna al guardar.", "tenue", bg=t.BLANCO).pack(side="left", padx=(14, 0))
        w.Boton(self.botones, "Guardar reparación", self.guardar).pack(side="right")
        w.Boton(self.botones, "Cancelar", self.cancelar, estilo="secundario").pack(side="right", padx=(0, 13))
        self.after(50, self.cliente.enfocar)

    def cancelar(self):
        for campo in (self.cliente, self.telefono, self.equipo, self.falla):
            campo.limpiar()
        self.app.mostrar("menu")

    def guardar(self):
        r = self.llamar("reparaciones.registrar", cliente=self.cliente.valor(), telefono=self.telefono.valor(),
                        equipo=self.equipo.valor(), falla=self.falla.valor())
        if r:
            self.actual = r
            self.app.aviso(f"Reparación #{r['idReparacion']} guardada en estado Pendiente.\n"
                           f"Fecha de ingreso: {r['fechaIngreso']}")
            self.app.mostrar("rep_estado")


class ActualizarEstado(PasoReparacion):
    """Paso 2 · CU-05."""

    paso = 2

    def contenido(self):
        c = self.cuerpo
        w.titulo_tarjeta(c, "Actualizar estado de la reparación", "Localiza la reparación y elige su nuevo estado.")
        self.localizador = Localizador(c, self.app, self._elegida)
        self.localizador.pack(fill="x")
        w.etiqueta(c, "Nuevo estado", "etiqueta", bg=t.BLANCO).pack(anchor="w", pady=(22, 8))
        self.estado = w.Opciones(c, [(e, n) for e, n in NOMBRE_ESTADO.items()])
        self.estado.pack(fill="x")
        w.Boton(self.botones, "Guardar estado", self.guardar).pack(side="right")
        w.Boton(self.botones, "Anterior", lambda: self.app.mostrar("rep_registrar"), estilo="secundario").pack(side="right", padx=(0, 13))
        if self.actual:
            self.localizador.elegir(self.actual)

    def _elegida(self, r):
        self.actual = r
        self.estado.fijar(r["estado"])

    def guardar(self):
        if not self.actual:
            self.app.aviso("Primero localiza la reparación.")
            return
        if not self.estado.valor():
            self.app.aviso("Elige el nuevo estado.")
            return
        r = self.llamar("reparaciones.actualizar_estado", idReparacion=self.actual["idReparacion"], estado=self.estado.valor())
        if r:
            self.actual = r
            self.app.aviso(f"Reparación #{r['idReparacion']}: estado «{r['nombreEstado']}» guardado.")
            self.app.mostrar("rep_refacciones")


class RefaccionesUsadas(PasoReparacion):
    """Paso 3 · flujo alterno 2.1 del CU-05: se indica el producto y la cantidad usada y se
    descuenta del inventario."""

    paso = 3

    def contenido(self):
        c = self.cuerpo
        r = self.actual
        sub = "Indica el producto y la cantidad usada. Se descuenta del inventario."
        if r:
            sub += f"   Reparación #{r['idReparacion']} · {r['cliente']} · {r['equipo']}"
        w.titulo_tarjeta(c, "Refacciones usadas", sub)
        fila = tk.Frame(c, bg=t.BLANCO)
        fila.pack(fill="x", pady=(0, 22))
        fila.columnconfigure(0, weight=1)
        prod = tk.Frame(fila, bg=t.BLANCO)
        prod.grid(row=0, column=0, sticky="ew", padx=(0, 18))
        cant = tk.Frame(fila, bg=t.BLANCO)
        cant.grid(row=0, column=1, sticky="ew", padx=(0, 18))
        self.producto = w.campo_con_titulo(prod, "Producto", lambda m: w.Selector(m, [], editable=True), pady=0)
        self.cantidad = w.campo_con_titulo(cant, "Cantidad", lambda m: w.Campo(m, "0", ancho=196), pady=0)
        boton = tk.Frame(fila, bg=t.BLANCO)
        boton.grid(row=0, column=2, sticky="s")
        w.Boton(boton, "Agregar refacción", self.agregar, alto=48).pack()
        self.producto.bind("<KeyRelease>", self._filtrar)
        self.tabla = w.Tabla(c, [("Producto", 60), ("Cantidad", 14), ("Descuento en inventario", 26)],
                             vacio="Todavía no se registran refacciones para esta reparación.")
        self.tabla.pack(fill="both", expand=True)
        w.Boton(self.botones, "Continuar", lambda: self.app.mostrar("rep_entrega")).pack(side="right")
        w.Boton(self.botones, "Anterior", lambda: self.app.mostrar("rep_estado"), estilo="secundario").pack(side="right", padx=(0, 13))
        self.descuentos = self.app.estado.setdefault("descuentos", {})
        if not r:
            self.tabla.cargar([])
            self.after(100, lambda: (self.app.aviso("Primero localiza la reparación en el paso 2."),
                                     self.app.mostrar("rep_estado")))
            return
        self._cargar_productos("")
        self._pintar(r)

    def _cargar_productos(self, texto):
        datos = self.llamar("reparaciones.refacciones_disponibles", idReparacion=self.actual["idReparacion"], texto=texto) or []
        self.producto.fijar_opciones([(p["idProducto"], f"{p['nombre']}  (existencia: {p['existencia']})") for p in datos])

    def _filtrar(self, e):
        if e.keysym in ("Up", "Down", "Return", "Escape"):
            return
        texto = self.producto.get()
        self._cargar_productos(texto.split("  (existencia")[0])

    def _pintar(self, r):
        filas = []
        for ref in r["refacciones"]:
            restante = self.descuentos.get(ref["idRefaccionUsada"])
            texto = f"−{ref['cantidad']}" + (f"  (quedan {restante})" if restante is not None else "")
            filas.append([ref["nombre"], ref["cantidad"], texto])
        self.tabla.cargar(filas)

    def agregar(self):
        pid = self.producto.valor()
        if pid is None:
            self.app.aviso("Elige un producto de la lista.")
            return
        r = self.llamar("reparaciones.registrar_refaccion", idReparacion=self.actual["idReparacion"], idProducto=pid,
                        cantidad=self.cantidad.valor())
        if r:
            self.descuentos[r["refacciones"][-1]["idRefaccionUsada"]] = r["existenciaRestante"]
            r.pop("existenciaRestante")
            bajo = r.pop("stockBajo")
            self.actual = r
            self.cantidad.limpiar()
            self.producto.set("")
            self._cargar_productos("")
            self._pintar(r)
            if bajo:
                self.app.aviso("La refacción quedó con stock bajo en la sucursal.")


class RegistrarEntrega(PasoReparacion):
    """Paso 4 · CU-06."""

    paso = 4

    def contenido(self):
        c = self.cuerpo
        w.titulo_tarjeta(c, "Entrega del equipo reparado", "Confirma que el equipo se entrega a su dueño y guarda la fecha de entrega.")
        self.localizador = Localizador(c, self.app, self._elegida, titulo_estado="Estado")
        self.localizador.pack(fill="x")
        caja = tk.Frame(c, bg=t.BLANCO)
        caja.pack(anchor="w", pady=(22, 0))
        self.fecha = w.campo_con_titulo(caja, "Fecha de entrega (dd/mm/aaaa)",
                                        lambda m: w.Campo(m, "dd/mm/aaaa", ancho=346, valor=date.today().strftime("%d/%m/%Y")))
        w.Pastilla(c, "La entrega solo se registra si la reparación está terminada", "amarillo", alto=32).pack(anchor="w")
        w.Boton(self.botones, "Guardar fecha de entrega", self.guardar).pack(side="right")
        w.Boton(self.botones, "Anterior", lambda: self.app.mostrar("rep_refacciones"), estilo="secundario").pack(side="right", padx=(0, 13))
        if self.actual:
            self.localizador.elegir(self.actual)

    def _elegida(self, r):
        self.actual = r

    def guardar(self):
        if not self.actual:
            self.app.aviso("Primero localiza la reparación.")
            return
        if not self.app.confirmar(f"¿Confirmas que el equipo «{self.actual['equipo']}» se entrega a "
                                  f"{self.actual['cliente']}?"):
            return
        r = self.llamar("reparaciones.registrar_entrega", idReparacion=self.actual["idReparacion"],
                        fechaEntrega=self.fecha.valor())
        if r:
            self.actual = r
            self.localizador.mostrar(r)
            self.app.aviso(f"Entrega de la reparación #{r['idReparacion']} registrada ({r['fechaEntrega']}).")


# ---------------------------------------------------------------------------
class ConsultarReparaciones(Pantalla):
    """CU-14 con el teléfono de contacto del cliente (resultado 3 de la evaluación)."""

    titulo = "Consultar reparaciones"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        izq, der = w.columnas_tarjetas(self, (860, 450), margen=(35, 34, 35, 34))
        w.titulo_tarjeta(izq, "Reparaciones registradas",
                         "Cliente, teléfono de contacto, equipo, estado y fechas. El historial se conserva al menos una semana.")
        self.tabla = w.Tabla(izq, [("Cliente", 15), ("Teléfono", 14), ("Equipo", 14), ("Estado", 16), ("Ingreso", 16),
                                   ("Entrega", 12), ("", 16)], al_seleccionar=self.ver, vacio="No hay reparaciones registradas.")
        self.tabla.pack(fill="both", expand=True)
        w.titulo_tarjeta(der, "Detalle de la reparación", "Incluye las refacciones usadas.")
        self.res = w.resumen(der, [("Cliente", "—"), ("Teléfono de contacto", "—"), ("Equipo", "—"), ("Estado", "—"),
                                   ("Falla reportada", "—")], columnas=2)
        self.res.pack(fill="x", pady=(0, 18))
        self.refacciones = w.Tabla(der, [("Refacción usada", 78), ("Cant.", 22)], vacio="Sin refacciones usadas.")
        self.refacciones.pack(fill="both", expand=True)
        self.refacciones.cargar([])
        datos = self.llamar("reparaciones.listar") or []
        filas = [[r["cliente"], r["telefono"], r["equipo"], r["nombreEstado"], r["fechaIngreso"][:10], r["fechaEntrega"] or "—",
                  lambda padre, k=k: w.enlace(padre, "Ver detalle", lambda: self.tabla.seleccionar(k), bg=padre.cget("bg"))]
                 for k, r in enumerate(datos)]
        self.tabla.cargar(filas, datos)
        if datos:
            self.tabla.seleccionar(0)

    def ver(self, r):
        d = self.llamar("reparaciones.obtener", idReparacion=r["idReparacion"])
        if not d:
            return
        v = self.res.valores
        v["Cliente"].configure(text=d["cliente"])
        v["Teléfono de contacto"].configure(text=d["telefono"])
        v["Equipo"].configure(text=d["equipo"])
        v["Estado"].configure(text=d["nombreEstado"])
        v["Falla reportada"].configure(text=d["falla"])
        self.refacciones.cargar([[x["nombre"], x["cantidad"]] for x in d["refacciones"]])


def registrar(app):
    app.registrar_pantalla("rep_registrar", RegistrarReparacion)
    app.registrar_pantalla("rep_estado", ActualizarEstado)
    app.registrar_pantalla("rep_refacciones", RefaccionesUsadas)
    app.registrar_pantalla("rep_entrega", RegistrarEntrega)
    app.registrar_pantalla("reparaciones", ConsultarReparaciones)
    app.registrar_tarjeta(TarjetaMenu("rep_registrar", "Registrar reparación", "Datos del cliente y equipo", "llave",
                                      (ROL_EMPLEADO,), DEL_EMPLEADO, {ROL_EMPLEADO: 3}))
    app.registrar_tarjeta(TarjetaMenu("reparaciones", "Consultar reparaciones", "Cliente, equipo, estado y refacciones",
                                      "llave", (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 5}))
