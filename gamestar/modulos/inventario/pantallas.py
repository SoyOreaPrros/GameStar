"""Pantallas de inventario: consulta compartida (2.2.2.C.b), catálogo de productos,
alertas de stock bajo y movimientos de inventario."""

from __future__ import annotations

import tkinter as tk

from gamestar.nucleo.reglas import LIMITE_STOCK_BAJO
from gamestar.ui import tema as t
from gamestar.ui import widgets as w
from gamestar.ui.app import (COMPARTIDA, ROL_ADMINISTRADOR, ROL_EMPLEADO, SOLO_ADMIN, Dialogo, Pantalla,
                             TarjetaMenu)

NOTA_STOCK_BAJO = (f"Stock bajo: cuando la existencia es de {'cinco' if LIMITE_STOCK_BAJO == 5 else LIMITE_STOCK_BAJO} "
                   "unidades o menos, o queda bajo el stock mínimo del producto.")


def pastilla_stock_bajo(padre):
    return w.Pastilla(padre, "Stock bajo", "amarillo", alto=32)


class ConsultarInventario(Pantalla):
    """CU-02: productos con existencias por sucursal, búsqueda por término y filtro por
    categoría (RF04, RF05, RF06). La búsqueda se actualiza mientras se escribe."""

    titulo = "Consultar inventario"
    pastilla = ("Función compartida", "plata")

    def construir(self):
        filtros = w.Tarjeta(self, pad=26)
        filtros.pack(fill="x", padx=35, pady=(34, 26))
        f = filtros.cuerpo
        f.columnconfigure(0, weight=1)
        bus = tk.Frame(f, bg=t.BLANCO)
        bus.grid(row=0, column=0, sticky="ew", padx=(0, 18))
        cat = tk.Frame(f, bg=t.BLANCO)
        cat.grid(row=0, column=1, sticky="ew")
        self.busqueda = w.campo_con_titulo(bus, "Buscar producto", lambda m: w.Campo(m, "Escribir un término de búsqueda"), pady=0)
        categorias = self.llamar("inventario.categorias") or []
        opciones = [(None, "Todas las categorías")] + [(c["idCategoria"], c["nombre"]) for c in categorias]
        self.categoria = w.campo_con_titulo(cat, "Categoría", lambda m: w.Selector(m, opciones, width=24), pady=0)
        self.categoria.current(0)
        self.categoria.bind("<<ComboboxSelected>>", lambda e: self.buscar())
        self.busqueda.al_escribir(self._programar)

        self.tabla_tarjeta = w.Tarjeta(self, pad=26, modo="xy")
        self.tabla_tarjeta.pack(fill="both", expand=True, padx=35)
        self.tabla_marco = self.tabla_tarjeta.cuerpo
        w.etiqueta(self, NOTA_STOCK_BAJO, "tenue").pack(anchor="w", padx=35, pady=(18, 30))
        self._pendiente = None
        self.tabla = None
        self.buscar()

    def _programar(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(220, self.buscar)

    def buscar(self):
        self._pendiente = None
        r = self.llamar("inventario.consultar", texto=self.busqueda.valor(), idCategoria=self.categoria.valor())
        if r is None:
            return
        if self.tabla is None:
            columnas = [("Producto", 26), ("Categoría", 15)]
            columnas += [(f"Existencia · {s['nombre']}", 22) for s in r["sucursales"]]
            columnas += [("Estado", 15)]
            self.tabla = w.Tabla(self.tabla_marco, columnas,
                                 vacio="Sin resultados: ningún producto coincide con la búsqueda.")
            self.tabla.pack(fill="both", expand=True)
        filas = []
        for p in r["productos"]:
            estado = pastilla_stock_bajo if p["stockBajo"] else ""
            filas.append([p["nombre"], p["categoria"], *[p["existencias"][str(s["idSucursal"])] for s in r["sucursales"]], estado])
        self.tabla.cargar(filas, r["productos"])


# ---------------------------------------------------------------------------
class GestionarCatalogo(Pantalla):
    """CU-07 registrar, CU-08 modificar y CU-09 eliminar productos."""

    titulo = "Gestionar catálogo de productos"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        self.categorias = [(c["idCategoria"], c["nombre"]) for c in (self.llamar("inventario.categorias") or [])]
        self.sucursales = [(s["idSucursal"], s["nombre"]) for s in (self.llamar("usuarios.sucursales") or [])]
        izq, der = w.columnas_tarjetas(self, (782, 510), margen=(35, 26, 35, 26))
        w.titulo_tarjeta(izq, "Productos registrados", "Modificar o eliminar productos del catálogo.")
        self.tabla = w.Tabla(izq, [("Producto", 24), ("Categoría", 17), ("Precio", 13), ("Stock mínimo", 13), ("Acciones", 26)],
                             vacio="No hay productos en el catálogo.")
        self.tabla.pack(fill="both", expand=True)

        w.titulo_tarjeta(der, "Registrar producto",
                         f"Alta de un producto con su existencia inicial en {self.app.usuario['sucursal']}.")
        self.nombre = w.campo_con_titulo(der, "Nombre", lambda m: w.Campo(m, "Nombre del producto"))
        self.categoria = w.campo_con_titulo(der, "Categoría", lambda m: w.Selector(m, self.categorias))
        if self.categorias:
            self.categoria.current(0)
        fila = tk.Frame(der, bg=t.BLANCO)
        fila.pack(fill="x")
        for i in (0, 1):
            fila.columnconfigure(i, weight=1, uniform="f")
        c1, c2 = tk.Frame(fila, bg=t.BLANCO), tk.Frame(fila, bg=t.BLANCO)
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 9))
        c2.grid(row=0, column=1, sticky="ew", padx=(9, 0))
        self.precio = w.campo_con_titulo(c1, "Precio", lambda m: w.Campo(m, "0.00"))
        self.minimo = w.campo_con_titulo(c2, "Stock mínimo", lambda m: w.Campo(m, "0"))
        self.inicial = w.campo_con_titulo(der, "Cantidad inicial", lambda m: w.Campo(m, "0"))
        w.Boton(der, "Guardar producto", self.registrar).pack(side="bottom", fill="x")
        self.cargar()

    def cargar(self):
        productos = self.llamar("inventario.catalogo") or []
        filas = []
        for p in productos:
            def acciones(padre, p=p):
                f = tk.Frame(padre, bg=padre.cget("bg"))
                w.enlace(f, "Modificar", lambda: self.modificar(p)).pack(side="left", padx=(0, 18))
                w.enlace(f, "Eliminar", lambda: self.eliminar(p), color=t.ROJO_TEXTO).pack(side="left")
                return f
            filas.append([p["nombre"], p["categoria"], p["precio"], p["stockMinimo"], acciones])
        self.tabla.cargar(filas, productos)

    def registrar(self):
        r = self.llamar("inventario.registrar_producto", nombre=self.nombre.valor(), idCategoria=self.categoria.valor(),
                        precio=self.precio.valor(), stockMinimo=self.minimo.valor(), cantidadInicial=self.inicial.valor() or 0)
        if r:
            for c in (self.nombre, self.precio, self.minimo, self.inicial):
                c.limpiar()
            self.app.aviso(f"Producto «{r['nombre']}» registrado con el identificador {r['idProducto']}.")
            self.cargar()

    def modificar(self, p):
        d = Dialogo(self.app, "Modificar producto", ancho=520)
        c = d.cuerpo
        nombre = w.campo_con_titulo(c, "Nombre", lambda m: w.Campo(m, "Nombre del producto", valor=p["nombre"], ancho=460))
        categoria = w.campo_con_titulo(c, "Categoría", lambda m: w.Selector(m, self.categorias))
        categoria.seleccionar(p["idCategoria"])
        fila = tk.Frame(c, bg=t.BLANCO)
        fila.pack(fill="x")
        for i in (0, 1):
            fila.columnconfigure(i, weight=1, uniform="f")
        c1, c2 = tk.Frame(fila, bg=t.BLANCO), tk.Frame(fila, bg=t.BLANCO)
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 9))
        c2.grid(row=0, column=1, sticky="ew", padx=(9, 0))
        precio = w.campo_con_titulo(c1, "Precio", lambda m: w.Campo(m, "0.00", valor=p["precio"]))
        minimo = w.campo_con_titulo(c2, "Stock mínimo", lambda m: w.Campo(m, "0", valor=p["stockMinimo"]))

        tk.Frame(c, bg=t.SEPARADOR, height=1).pack(fill="x", pady=(4, 14))
        w.etiqueta(c, "Entrada de mercancía (opcional)", "cuerpo_negrita", bg=t.BLANCO).pack(anchor="w")
        w.etiqueta(c, "Unidades que ingresan al inventario de una sucursal.", "tenue", bg=t.BLANCO).pack(anchor="w", pady=(2, 10))
        fila2 = tk.Frame(c, bg=t.BLANCO)
        fila2.pack(fill="x")
        for i in (0, 1):
            fila2.columnconfigure(i, weight=1, uniform="f")
        e1, e2 = tk.Frame(fila2, bg=t.BLANCO), tk.Frame(fila2, bg=t.BLANCO)
        e1.grid(row=0, column=0, sticky="ew", padx=(0, 9))
        e2.grid(row=0, column=1, sticky="ew", padx=(9, 0))
        sucursal = w.campo_con_titulo(e1, "Sucursal", lambda m: w.Selector(m, self.sucursales, width=12))
        sucursal.seleccionar(self.app.usuario["idSucursal"])
        cantidad = w.campo_con_titulo(e2, "Cantidad", lambda m: w.Campo(m, "0"))

        def guardar():
            r = self.llamar("inventario.modificar_producto", idProducto=p["idProducto"], nombre=nombre.valor(),
                            idCategoria=categoria.valor(), precio=precio.valor(), stockMinimo=minimo.valor())
            if not r:
                return
            if cantidad.valor().strip() not in ("", "0"):
                if not self.llamar("inventario.registrar_entrada", idProducto=p["idProducto"],
                                   idSucursal=sucursal.valor(), cantidad=cantidad.valor()):
                    d.resultado = r  # los datos del producto sí se guardaron
                    return
            d.resultado = r
            d.destroy()

        d.botones("Guardar cambios", guardar)
        d.mostrar()
        if d.resultado:
            self.cargar()

    def eliminar(self, p):
        # CU-09: solicitar confirmación; si se cancela no se elimina nada (flujo alterno 3.1).
        if not self.app.confirmar(f"¿Eliminar «{p['nombre']}» del catálogo?"):
            return
        if self.llamar("inventario.eliminar_producto", idProducto=p["idProducto"]):
            self.app.aviso(f"Producto «{p['nombre']}» eliminado.")
            self.cargar()


# ---------------------------------------------------------------------------
class AlertasStock(Pantalla):
    """CU-16: productos por reabastecer con su categoría (resultado 2 de la evaluación),
    sucursal, existencia actual y mínimo; permite ajustar el stock mínimo (CU-08)."""

    titulo = "Supervisar alertas de stock bajo"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        tarjeta = w.Tarjeta(self, pad=26, modo="xy")
        tarjeta.pack(fill="both", expand=True, padx=35, pady=34)
        w.titulo_tarjeta(tarjeta.cuerpo, "Productos por reabastecer",
                         "Productos con cinco unidades o menos, o por debajo de su stock mínimo.")
        self.tabla = w.Tabla(tarjeta.cuerpo, [("Producto", 22), ("Categoría", 13), ("Sucursal", 12),
                                              ("Existencia actual", 15), ("Stock mínimo", 12), ("Estado", 12), ("", 18)],
                             vacio="No hay productos con stock bajo.")
        self.tabla.pack(fill="both", expand=True)
        self.cargar()

    def cargar(self):
        datos = self.llamar("inventario.alertas") or []
        filas = [[a["nombre"], a["categoria"], a["sucursal"], a["existencia"], a["stockMinimo"], pastilla_stock_bajo,
                  lambda padre, a=a: w.enlace(padre, "Ajustar stock mínimo", lambda: self.ajustar(a), bg=padre.cget("bg"))]
                 for a in datos]
        self.tabla.cargar(filas, datos)

    def ajustar(self, a):
        d = Dialogo(self.app, "Ajustar stock mínimo", ancho=420)
        w.etiqueta(d.cuerpo, f"{a['nombre']} · {a['categoria']}", "tenue", bg=t.BLANCO).pack(anchor="w", pady=(0, 14))
        minimo = w.campo_con_titulo(d.cuerpo, "Stock mínimo", lambda m: w.Campo(m, "0", valor=a["stockMinimo"], ancho=360))

        def guardar():
            r = self.llamar("inventario.ajustar_stock_minimo", idProducto=a["idProducto"], stockMinimo=minimo.valor())
            if r:
                d.resultado = r
                d.destroy()

        d.botones("Guardar", guardar)
        if d.mostrar():
            self.cargar()


class MovimientosInventario(Pantalla):
    """Entradas y salidas registradas (RFBD07): tipo, cantidad y fecha de cada movimiento."""

    titulo = "Consultar movimientos de inventario"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        tarjeta = w.Tarjeta(self, pad=26, modo="xy")
        tarjeta.pack(fill="both", expand=True, padx=35, pady=34)
        w.titulo_tarjeta(tarjeta.cuerpo, "Entradas y salidas registradas", "Tipo, cantidad y fecha de cada movimiento.")
        tabla = w.Tabla(tarjeta.cuerpo, [("Producto", 30), ("Sucursal", 14), ("Tipo", 16), ("Cantidad", 14), ("Fecha", 20)],
                        vacio="Todavía no hay movimientos registrados.")
        tabla.pack(fill="both", expand=True)
        datos = self.llamar("inventario.movimientos", limite=500) or []
        tabla.cargar([[m["producto"], m["sucursal"], m["tipo"].capitalize(), m["cantidad"], m["fecha"]] for m in datos])


def _indicador_alertas(app):
    """Notificación al administrador cuando hay stock bajo (RFBD12, paso 2 del CU-16)."""
    n = app.llamar("inventario.contar_alertas")
    if not n:
        return None
    if not app.estado.get("alertas_notificadas"):
        app.estado["alertas_notificadas"] = True
        app.after(400, lambda: app.aviso(f"Hay {n} registro(s) de productos con stock bajo por reabastecer.",
                                         "Alertas de stock bajo"))
    return f"{n} alerta{'s' if n != 1 else ''}"


def registrar(app):
    app.registrar_pantalla("inventario", ConsultarInventario)
    app.registrar_pantalla("catalogo", GestionarCatalogo)
    app.registrar_pantalla("alertas", AlertasStock)
    app.registrar_pantalla("movimientos", MovimientosInventario)
    app.registrar_tarjeta(TarjetaMenu("inventario", "Consultar inventario", "Buscar y filtrar productos\nVer existencia por sucursal",
                                      "caja", (ROL_EMPLEADO, ROL_ADMINISTRADOR), COMPARTIDA,
                                      {ROL_EMPLEADO: 1, ROL_ADMINISTRADOR: 1}))
    app.registrar_tarjeta(TarjetaMenu("catalogo", "Gestionar catálogo de productos", "Registrar / modificar / eliminar",
                                      "lista", (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 2}))
    app.registrar_tarjeta(TarjetaMenu("alertas", "Supervisar alertas de stock bajo", "Existencia y stock mínimo",
                                      "alerta", (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 8},
                                      indicador=_indicador_alertas))
    app.registrar_tarjeta(TarjetaMenu("movimientos", "Consultar movimientos de inventario", "Entradas y salidas registradas",
                                      "flechas", (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 9}))
