"""Pantallas de ventas: registrar venta (2.2.2.C.c), registro de venta confirmada y
consulta del historial de ventas (administrador)."""

from __future__ import annotations

import tkinter as tk
import uuid
from decimal import Decimal
from pathlib import Path

from gamestar.modulos.ventas.comprobante import abrir, guardar_comprobante
from gamestar.ui import tema as t
from gamestar.ui import widgets as w
from gamestar.ui.app import DEL_EMPLEADO, ROL_ADMINISTRADOR, ROL_EMPLEADO, SOLO_ADMIN, Pantalla, TarjetaMenu


class RegistrarVenta(Pantalla):
    """CU-03. Flujo de no más de tres interacciones (RNF05): indicar la cantidad, «Agregar»
    y «Confirmar venta». La búsqueda filtra la lista mientras se escribe."""

    titulo = "Registrar venta"
    roles = (ROL_EMPLEADO,)

    def construir(self):
        self.clave = uuid.uuid4().hex  # identifica esta venta aunque se reintente (RNF02)
        self.carrito: dict[int, dict] = {}
        self.existencias: dict[int, int] = {}
        izq, der = w.columnas_tarjetas(self, (744, 547), margen=(35, 34, 35, 34))

        w.titulo_tarjeta(izq, "Seleccionar productos y cantidades", "Busca y agrega productos a la venta.")
        self.busqueda = w.campo_con_titulo(izq, "Buscar producto", lambda m: w.Campo(m, "Escribir un término de búsqueda"),
                                           pady=(0, 20))
        self.busqueda.al_escribir(self._programar)
        self.productos = w.Tabla(izq, [("Producto", 44), ("Existencia", 21), ("Cantidad", 18), ("", 17)], alto_fila=17,
                                 vacio="Sin resultados: ningún producto coincide con la búsqueda.")
        self.productos.pack(fill="both", expand=True)

        w.titulo_tarjeta(der, "Venta actual", "Productos agregados con su precio vigente.")
        botones = tk.Frame(der, bg=t.BLANCO)
        botones.pack(side="bottom", fill="x")
        botones.columnconfigure(0, weight=37, uniform="b")
        botones.columnconfigure(1, weight=48, uniform="b")
        w.Boton(botones, "Cancelar", self.cancelar, estilo="secundario").grid(row=0, column=0, sticky="ew", padx=(0, 13))
        self.boton_confirmar = w.Boton(botones, "Confirmar venta", self.confirmar)
        self.boton_confirmar.grid(row=0, column=1, sticky="ew")
        self.venta = w.Tabla(der, [("Producto", 56), ("Cant.", 19), ("Precio", 25)], desplazable=True,
                             vacio="Aún no hay productos en la venta.")
        self.venta.pack(fill="x")
        self.venta.pack_propagate(False)
        total =w.Tarjeta(der, padx=14, pady=16, radio=10, relleno=t.FONDO, borde=t.FONDO)
        total.pack(fill="x", pady=(16, 0))
        w.etiqueta(total.cuerpo, "Total", "grande", bg=t.FONDO).pack(side="left")
        self.total = w.etiqueta(total.cuerpo, "0.00", "grande", color=t.TEXTO_TENUE, bg=t.FONDO)
        self.total.pack(side="right")
        self._pendiente = None
        self.buscar()
        self._pintar_venta()

    # -- productos ----------------------------------------------------------
    def _programar(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(220, self.buscar)

    def buscar(self):
        self._pendiente = None
        datos = self.llamar("ventas.productos", texto=self.busqueda.valor())
        if datos is None:
            return
        self.existencias.update({p["idProducto"]: p["existencia"] for p in datos})
        filas = []
        for p in datos:
            campo = {}

            def cantidad(padre, p=p, campo=campo):
                c = w.Campo(padre, "0", ancho=92, alto=42)
                c.al_enter(lambda: self.agregar(p, c))
                campo["c"] = c
                return c

            def boton(padre, p=p, campo=campo):
                return w.Boton(padre, "Agregar", lambda: self.agregar(p, campo["c"]), estilo="secundario", alto=42, ancho=100)

            filas.append([p["nombre"], p["existencia"], cantidad, boton])
        self.productos.cargar(filas, datos)

    def agregar(self, p, campo):
        texto = campo.valor().strip()
        try:
            n = int(texto)
        except ValueError:
            n = 0
        if n <= 0:
            self.app.aviso("Escribe una cantidad mayor que 0.")
            campo.enfocar()
            return
        en_venta = self.carrito.get(p["idProducto"], {}).get("cantidad", 0)
        disponible = self.existencias.get(p["idProducto"], p["existencia"])
        if en_venta + n > disponible:  # excepción 3.1 del CU-03
            self.app.aviso(f"La cantidad supera las existencias de «{p['nombre']}» en la sucursal "
                           f"(disponibles: {disponible - en_venta}). Ajusta la cantidad.")
            campo.enfocar()
            return
        linea = self.carrito.setdefault(p["idProducto"], {"nombre": p["nombre"], "precio": p["precio"], "cantidad": 0})
        linea["cantidad"] += n
        campo.limpiar()
        self._pintar_venta()

    # -- venta actual -------------------------------------------------------
    def _pintar_venta(self):
        filas = [[l["nombre"], l["cantidad"], l["precio"]] for l in self.carrito.values()]
        self.venta.cargar(filas)
        total = sum(Decimal(l["precio"]) * l["cantidad"] for l in self.carrito.values())
        self.total.configure(text=f"{total:.2f}")
        self.boton_confirmar.habilitar(bool(self.carrito))
        self.venta.configure(height=min(360, 60 + 52 * max(1, len(filas))))

    def cancelar(self):
        # Flujo alterno 5.1: descartar la venta sin guardar nada.
        if self.carrito and not self.app.confirmar("¿Descartar la venta en curso?"):
            return
        self.app.mostrar("menu")

    def confirmar(self):
        if not self.carrito:
            self.app.aviso("Agrega al menos un producto a la venta.")
            return
        lineas = [{"idProducto": pid, "cantidad": l["cantidad"]} for pid, l in self.carrito.items()]
        r = self.llamar("ventas.registrar", lineas=lineas, claveOperacion=self.clave)
        if r:
            self.app.mostrar("registro_venta", venta=r)
        elif self.app.ultimo_error == "validacion":
            self.buscar()  # existencias actualizadas por si la otra laptop vendió el producto
        # Sin conexión: la venta en curso se conserva con la misma clave; al reintentar no se duplica.


class RegistroVenta(Pantalla):
    """Venta confirmada con el precio unitario del momento; permite emitir el registro
    (comprobante digital), iniciar una nueva venta o volver al menú."""

    titulo = "Registro de venta"
    volver = "ventas"
    texto_volver = "Registrar venta"
    roles = (ROL_EMPLEADO,)

    def construir(self, venta):
        self.v = venta
        izq, der = w.columnas_tarjetas(self, (945, 347), modo="x", margen=(35, 34, 35, 34))
        izq.master.grid_configure(sticky="nsew")
        w.titulo_tarjeta(izq, "Venta confirmada", "Registro de la venta con el precio unitario del momento.")
        w.resumen(izq, [("Fecha", venta["fecha"]), ("Usuario", venta["usuario"]), ("Sucursal", venta["sucursal"]),
                        ("Total", venta["total"])]).pack(fill="x", pady=(0, 22))
        tabla = w.Tabla(izq, [("Producto", 44), ("Cantidad", 23), ("Precio unitario", 33)], desplazable=False)
        tabla.pack(fill="x")
        tabla.cargar([[r["nombre"], r["cantidad"], r["precioUnitario"]] for r in venta["renglones"]])
        if venta.get("stockBajo"):
            nombres = ", ".join(f"{p['nombre']} ({p['existencia']})" for p in venta["stockBajo"])
            aviso = tk.Frame(izq, bg=t.BLANCO)
            aviso.pack(fill="x", pady=(20, 0))
            w.Pastilla(aviso, "Stock bajo", "amarillo").pack(side="left", anchor="n")
            w.etiqueta_ajustable(aviso, f"Quedaron con stock bajo: {nombres}.", "tenue", bg=t.BLANCO).pack(
                side="left", fill="x", expand=True, padx=(12, 0))

        w.titulo_tarjeta(der, "Acciones", pady=(0, 18))
        w.Boton(der, "Emitir registro de venta", self.emitir).pack(fill="x", pady=(0, 14))
        w.Boton(der, "Nueva venta", lambda: self.app.mostrar("ventas"), estilo="secundario").pack(fill="x", pady=(0, 14))
        w.Boton(der, "Menú principal", lambda: self.app.mostrar("menu"), estilo="secundario").pack(fill="x")

    def emitir(self):
        ruta = guardar_comprobante(self.v, Path(self.app.cfg.carpeta_comprobantes))
        abrir(ruta)
        self.app.aviso(f"Registro de venta emitido:\n{ruta}")


class HistorialVentas(Pantalla):
    """CU-13: historial con fecha, usuario, sucursal y total; al seleccionar una venta se
    muestra su detalle con el precio unitario del momento."""

    titulo = "Consultar historial de ventas"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        izq, der = w.columnas_tarjetas(self, (744, 547), margen=(35, 34, 35, 34))
        w.titulo_tarjeta(izq, "Historial de ventas", "Fecha, usuario, sucursal y total de cada venta.")
        self.tabla = w.Tabla(izq, [("Fecha", 30), ("Usuario", 22), ("Sucursal", 17), ("Total", 14), ("", 17)],
                             al_seleccionar=self.ver_detalle, vacio="No hay ventas registradas.")
        self.tabla.pack(fill="both", expand=True)
        w.titulo_tarjeta(der, "Detalle de la venta", "Productos, cantidades y precio unitario del momento.")
        self.res = w.resumen(der, [("Fecha", "—"), ("Total", "—")])
        self.res.pack(fill="x", pady=(0, 22))
        self.detalle = w.Tabla(der, [("Producto", 50), ("Cant.", 17), ("Precio unitario", 33)],
                               vacio="Selecciona una venta para ver su detalle.")
        self.detalle.pack(fill="both", expand=True)
        self.detalle.cargar([])
        ventas = self.llamar("ventas.historial") or []
        filas = [[v["fecha"], v["usuario"], v["sucursal"], v["total"],
                  lambda padre, k=k: w.enlace(padre, "Ver detalle", lambda: self.tabla.seleccionar(k), bg=padre.cget("bg"))]
                 for k, v in enumerate(ventas)]
        self.tabla.cargar(filas, ventas)
        if ventas:
            self.tabla.seleccionar(0)

    def ver_detalle(self, v):
        d = self.llamar("ventas.detalle", idVenta=v["idVenta"])
        if not d:
            return
        self.res.valores["Fecha"].configure(text=d["fecha"])
        self.res.valores["Total"].configure(text=d["total"])
        self.detalle.cargar([[r["nombre"], r["cantidad"], r["precioUnitario"]] for r in d["renglones"]])


def registrar(app):
    app.registrar_pantalla("ventas", RegistrarVenta)
    app.registrar_pantalla("registro_venta", RegistroVenta)
    app.registrar_pantalla("historial_ventas", HistorialVentas)
    app.registrar_tarjeta(TarjetaMenu("ventas", "Registrar venta", "Seleccionar productos y cantidades\nConfirmar venta",
                                      "carrito", (ROL_EMPLEADO,), DEL_EMPLEADO, {ROL_EMPLEADO: 2}))
    app.registrar_tarjeta(TarjetaMenu("historial_ventas", "Consultar historial de ventas", "Ver detalle por venta",
                                      "reloj", (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 4}))
