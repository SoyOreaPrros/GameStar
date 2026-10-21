"""Lógica de negocio del catálogo, existencias por sucursal y movimientos."""

from __future__ import annotations

import unicodedata

from gamestar.modulos.reportes_bitacora.bitacora import registrar as bitacora
from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorValidacion
from gamestar.nucleo.reglas import SQL_STOCK_BAJO, es_stock_bajo
from gamestar.nucleo.servicios import ADMINISTRADOR, AMBOS, servicio


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para que la búsqueda encuentre "Zelda" o "zelda"."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


# ---------------------------------------------------------------------------
# Operaciones internas usadas por ventas y reparaciones
# ---------------------------------------------------------------------------
def movimiento(con, id_inventario: int, tipo: str, cantidad: int) -> None:
    """RFBD07: toda entrada o salida deja un registro con tipo, cantidad y fecha."""
    con.execute("INSERT INTO movimientoinventario (idInventario, tipo, cantidad, fecha) VALUES (?,?,?,?)",
                (id_inventario, tipo, cantidad, db.ahora()))


def registro_inventario(con, id_producto: int, id_sucursal: int) -> dict:
    fila = db.fila(con.execute(
        "SELECT i.idInventario, i.existencia, p.nombre, p.stockMinimo FROM inventario i "
        "JOIN producto p ON p.idProducto = i.idProducto WHERE i.idProducto = ? AND i.idSucursal = ?",
        (id_producto, id_sucursal)))
    if fila is None:
        if not con.execute("SELECT 1 FROM producto WHERE idProducto = ?", (id_producto,)).fetchone():
            raise ErrorValidacion("El producto seleccionado no existe.")
        cur = con.execute("INSERT INTO inventario (idProducto, idSucursal, existencia) VALUES (?,?,0)",
                          (id_producto, id_sucursal))
        return registro_inventario(con, id_producto, id_sucursal) | {"idInventario": cur.lastrowid}
    return fila


def salida(con, id_producto: int, id_sucursal: int, cantidad: int) -> dict:
    """Descuenta existencias de una sucursal (venta, RFBD06; refacción, RFBD08).
    Rechaza la operación si la cantidad supera la existencia (excepción 3.1 del CU-03)."""
    inv = registro_inventario(con, id_producto, id_sucursal)
    if cantidad > inv["existencia"]:
        raise ErrorValidacion(f"«{inv['nombre']}»: la cantidad ({cantidad}) supera las existencias de la "
                              f"sucursal ({inv['existencia']}). Ajusta la cantidad.")
    nueva = inv["existencia"] - cantidad
    con.execute("UPDATE inventario SET existencia = ? WHERE idInventario = ?", (nueva, inv["idInventario"]))
    movimiento(con, inv["idInventario"], "SALIDA", cantidad)
    return {"idProducto": id_producto, "nombre": inv["nombre"], "existencia": nueva,
            "stockBajo": es_stock_bajo(nueva, inv["stockMinimo"])}


def entrada(con, id_producto: int, id_sucursal: int, cantidad: int) -> dict:
    inv = registro_inventario(con, id_producto, id_sucursal)
    nueva = inv["existencia"] + cantidad
    con.execute("UPDATE inventario SET existencia = ? WHERE idInventario = ?", (nueva, inv["idInventario"]))
    movimiento(con, inv["idInventario"], "ENTRADA", cantidad)
    return {"idProducto": id_producto, "existencia": nueva}


# ---------------------------------------------------------------------------
# Consulta (CU-02)
# ---------------------------------------------------------------------------
def _sucursales(con):
    return db.filas(con.execute("SELECT idSucursal, nombre FROM sucursal ORDER BY idSucursal"))


@servicio("inventario.categorias", roles=AMBOS)
def categorias(ctx):
    return db.filas(ctx.con.execute("SELECT idCategoria, nombre FROM categoria ORDER BY idCategoria"))


@servicio("inventario.consultar", roles=AMBOS)
def consultar(ctx, texto="", idCategoria=None):
    """RF04 consultar, RF05 buscar por término, RF06 filtrar por categoría; existencias por
    sucursal (RFBD03). Solo lectura: no modifica ningún dato."""
    sucursales = _sucursales(ctx.con)
    sql = ("SELECT p.idProducto, p.nombre, p.precio, p.stockMinimo, p.idCategoria, c.nombre AS categoria "
           "FROM producto p JOIN categoria c ON c.idCategoria = p.idCategoria")
    params = []
    if idCategoria not in (None, "", 0):
        sql += " WHERE p.idCategoria = ?"
        params.append(db.entero(idCategoria, "Categoría", 1))
    productos = db.filas(ctx.con.execute(sql + " ORDER BY p.nombre COLLATE NOCASE", params))
    buscado = normalizar(texto)
    if buscado:
        productos = [p for p in productos if buscado in normalizar(p["nombre"])]
    existencias = {}
    for r in ctx.con.execute("SELECT idProducto, idSucursal, existencia FROM inventario"):
        existencias.setdefault(r["idProducto"], {})[r["idSucursal"]] = r["existencia"]
    for p in productos:
        exis = existencias.get(p["idProducto"], {})
        p["existencias"] = {str(s["idSucursal"]): exis.get(s["idSucursal"], 0) for s in sucursales}
        p["stockBajo"] = any(es_stock_bajo(e, p["stockMinimo"]) for e in p["existencias"].values())
        p["precio"] = db.de_centavos(p["precio"])
    return {"sucursales": sucursales, "productos": productos}


# ---------------------------------------------------------------------------
# Catálogo (CU-07, CU-08, CU-09)
# ---------------------------------------------------------------------------
def _datos_producto(con, nombre, idCategoria, precio, stockMinimo):
    nombre = db.texto(nombre, "Nombre", 100)
    id_categoria = db.entero(idCategoria, "Categoría", 1)
    if not con.execute("SELECT 1 FROM categoria WHERE idCategoria = ?", (id_categoria,)).fetchone():
        raise ErrorValidacion("Categoría: selecciona una categoría del catálogo.")
    centavos = db.a_centavos(precio, "Precio")
    if centavos <= 0:
        raise ErrorValidacion("Precio: debe ser mayor que 0.")
    minimo = db.entero(stockMinimo, "Stock mínimo", 0)
    return nombre, id_categoria, centavos, minimo


def _producto(con, id_producto) -> dict:
    p = db.fila(con.execute("SELECT * FROM producto WHERE idProducto = ?", (db.entero(id_producto, "Producto", 1),)))
    if not p:
        raise ErrorValidacion("El producto seleccionado no existe.")
    return p


@servicio("inventario.registrar_producto", roles=[ADMINISTRADOR], escritura=True)
def registrar_producto(ctx, nombre, idCategoria, precio, stockMinimo, cantidadInicial=0):
    """CU-07: alta en el catálogo con identificador único y su existencia inicial. Se crea un
    registro de inventario por sucursal (RFBD03); la cantidad inicial se asigna a la sucursal
    del administrador que registra."""
    nombre, id_categoria, centavos, minimo = _datos_producto(ctx.con, nombre, idCategoria, precio, stockMinimo)
    inicial = db.entero(cantidadInicial if str(cantidadInicial).strip() else 0, "Cantidad inicial", 0)
    cur = ctx.con.execute("INSERT INTO producto (nombre, precio, stockMinimo, idCategoria) VALUES (?,?,?,?)",
                          (nombre, centavos, minimo, id_categoria))
    id_producto = cur.lastrowid
    for s in _sucursales(ctx.con):
        ctx.con.execute("INSERT INTO inventario (idProducto, idSucursal, existencia) VALUES (?,?,0)",
                        (id_producto, s["idSucursal"]))
    if inicial > 0:
        entrada(ctx.con, id_producto, ctx.id_sucursal, inicial)
    bitacora(ctx.con, ctx.id_usuario, f"Registrar producto #{id_producto} ({nombre})", "Producto")
    return {"idProducto": id_producto, "nombre": nombre}


@servicio("inventario.catalogo", roles=[ADMINISTRADOR])
def catalogo(ctx):
    filas = db.filas(ctx.con.execute(
        "SELECT p.idProducto, p.nombre, p.precio, p.stockMinimo, p.idCategoria, c.nombre AS categoria "
        "FROM producto p JOIN categoria c ON c.idCategoria = p.idCategoria ORDER BY p.nombre COLLATE NOCASE"))
    for f in filas:
        f["precio"] = db.de_centavos(f["precio"])
    return filas


@servicio("inventario.modificar_producto", roles=[ADMINISTRADOR], escritura=True)
def modificar_producto(ctx, idProducto, nombre, idCategoria, precio, stockMinimo):
    """CU-08. Las ventas pasadas conservan su precio original (RFBD04): el precio cobrado
    vive en cada renglón de venta, no en el producto."""
    p = _producto(ctx.con, idProducto)
    nombre, id_categoria, centavos, minimo = _datos_producto(ctx.con, nombre, idCategoria, precio, stockMinimo)
    ctx.con.execute("UPDATE producto SET nombre = ?, idCategoria = ?, precio = ?, stockMinimo = ? WHERE idProducto = ?",
                    (nombre, id_categoria, centavos, minimo, p["idProducto"]))
    bitacora(ctx.con, ctx.id_usuario, f"Modificar producto #{p['idProducto']} ({nombre})", "Producto")
    return {"idProducto": p["idProducto"], "nombre": nombre}


@servicio("inventario.ajustar_stock_minimo", roles=[ADMINISTRADOR], escritura=True)
def ajustar_stock_minimo(ctx, idProducto, stockMinimo):
    """Flujo alterno 5.1 del CU-16: ajustar el stock mínimo mediante el CU-08."""
    p = _producto(ctx.con, idProducto)
    minimo = db.entero(stockMinimo, "Stock mínimo", 0)
    ctx.con.execute("UPDATE producto SET stockMinimo = ? WHERE idProducto = ?", (minimo, p["idProducto"]))
    bitacora(ctx.con, ctx.id_usuario, f"Modificar stock mínimo del producto #{p['idProducto']} a {minimo}", "Producto")
    return {"idProducto": p["idProducto"], "stockMinimo": minimo}


@servicio("inventario.registrar_entrada", roles=[ADMINISTRADOR], escritura=True)
def registrar_entrada(ctx, idProducto, idSucursal, cantidad):
    """Entrada de mercancía al inventario de una sucursal (glosario "Entrada / Salida", RFBD07)."""
    p = _producto(ctx.con, idProducto)
    id_sucursal = db.entero(idSucursal, "Sucursal", 1)
    if not ctx.con.execute("SELECT 1 FROM sucursal WHERE idSucursal = ?", (id_sucursal,)).fetchone():
        raise ErrorValidacion("Sucursal: selecciona una sucursal registrada.")
    cantidad = db.entero(cantidad, "Cantidad", 1)
    r = entrada(ctx.con, p["idProducto"], id_sucursal, cantidad)
    bitacora(ctx.con, ctx.id_usuario, f"Entrada de {cantidad} u. del producto #{p['idProducto']}", "Inventario")
    return r


@servicio("inventario.eliminar_producto", roles=[ADMINISTRADOR], escritura=True)
def eliminar_producto(ctx, idProducto):
    """CU-09 / RFBD11: se impide eliminar un producto con existencias o con historial en ventas,
    refacciones usadas o movimientos, para no dejar referencias rotas."""
    p = _producto(ctx.con, idProducto)
    pid = p["idProducto"]
    motivos = []
    if ctx.con.execute("SELECT 1 FROM inventario WHERE idProducto = ? AND existencia > 0", (pid,)).fetchone():
        motivos.append("tiene existencias en inventario")
    if ctx.con.execute("SELECT 1 FROM detalleventa WHERE idProducto = ?", (pid,)).fetchone():
        motivos.append("aparece en ventas registradas")
    if ctx.con.execute("SELECT 1 FROM refaccionusada WHERE idProducto = ?", (pid,)).fetchone():
        motivos.append("se usó como refacción en reparaciones")
    if ctx.con.execute("SELECT 1 FROM movimientoinventario m JOIN inventario i ON i.idInventario = m.idInventario "
                       "WHERE i.idProducto = ?", (pid,)).fetchone():
        motivos.append("tiene movimientos de inventario registrados")
    if motivos:
        raise ErrorValidacion(f"No se puede eliminar «{p['nombre']}»: " + "; ".join(motivos) + ".")
    ctx.con.execute("DELETE FROM inventario WHERE idProducto = ?", (pid,))
    ctx.con.execute("DELETE FROM producto WHERE idProducto = ?", (pid,))
    bitacora(ctx.con, ctx.id_usuario, f"Eliminar producto #{pid} ({p['nombre']})", "Producto")
    return {"idProducto": pid}


# ---------------------------------------------------------------------------
# Alertas de stock bajo (CU-16, RF07, RFBD12) y movimientos
# ---------------------------------------------------------------------------
@servicio("inventario.alertas", roles=[ADMINISTRADOR])
def alertas(ctx):
    return db.filas(ctx.con.execute(
        "SELECT p.idProducto, p.nombre, c.nombre AS categoria, s.idSucursal, s.nombre AS sucursal, "
        "i.existencia, p.stockMinimo FROM inventario i JOIN producto p ON p.idProducto = i.idProducto "
        "JOIN categoria c ON c.idCategoria = p.idCategoria JOIN sucursal s ON s.idSucursal = i.idSucursal "
        f"WHERE {SQL_STOCK_BAJO} ORDER BY i.existencia, p.nombre COLLATE NOCASE"))


@servicio("inventario.contar_alertas", roles=[ADMINISTRADOR])
def contar_alertas(ctx):
    return ctx.con.execute("SELECT COUNT(*) FROM inventario i JOIN producto p ON p.idProducto = i.idProducto "
                           f"WHERE {SQL_STOCK_BAJO}").fetchone()[0]


@servicio("inventario.movimientos", roles=[ADMINISTRADOR])
def movimientos(ctx, limite=500):
    limite = max(1, min(5000, db.entero(limite, "Límite", 1)))
    return db.filas(ctx.con.execute(
        "SELECT m.idMovimiento, p.nombre AS producto, s.nombre AS sucursal, m.tipo, m.cantidad, m.fecha "
        "FROM movimientoinventario m JOIN inventario i ON i.idInventario = m.idInventario "
        "JOIN producto p ON p.idProducto = i.idProducto JOIN sucursal s ON s.idSucursal = i.idSucursal "
        "ORDER BY m.fecha DESC, m.idMovimiento DESC LIMIT ?", (limite,)))
