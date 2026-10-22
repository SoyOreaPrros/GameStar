"""Lógica de negocio de ventas."""

from __future__ import annotations

from gamestar.modulos.inventario.servicios import normalizar, salida
from gamestar.modulos.reportes_bitacora.bitacora import registrar as bitacora
from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorValidacion
from gamestar.nucleo.servicios import ADMINISTRADOR, EMPLEADO, servicio


@servicio("ventas.productos", roles=[EMPLEADO])
def productos(ctx, texto=""):
    """Productos con su precio vigente y la existencia disponible en la sucursal del empleado."""
    filas = db.filas(ctx.con.execute(
        "SELECT p.idProducto, p.nombre, p.precio, COALESCE(i.existencia, 0) AS existencia "
        "FROM producto p LEFT JOIN inventario i ON i.idProducto = p.idProducto AND i.idSucursal = ? "
        "ORDER BY p.nombre COLLATE NOCASE", (ctx.id_sucursal,)))
    buscado = normalizar(texto)
    if buscado:
        filas = [f for f in filas if buscado in normalizar(f["nombre"])]
    for f in filas:
        f["precio"] = db.de_centavos(f["precio"])
    return filas


def _detalle(con, id_venta: int) -> dict:
    v = db.fila(con.execute(
        "SELECT v.idVenta, v.fecha, v.total, v.idUsuario, u.nombre AS usuario, v.idSucursal, s.nombre AS sucursal "
        "FROM venta v JOIN usuario u ON u.idUsuario = v.idUsuario JOIN sucursal s ON s.idSucursal = v.idSucursal "
        "WHERE v.idVenta = ?", (id_venta,)))
    if not v:
        raise ErrorValidacion("La venta seleccionada no existe.")
    v["total"] = db.de_centavos(v["total"])
    v["renglones"] = db.filas(con.execute(
        "SELECT d.idProducto, p.nombre, d.cantidad, d.precioUnitario FROM detalleventa d "
        "JOIN producto p ON p.idProducto = d.idProducto WHERE d.idVenta = ? ORDER BY d.idDetalleVenta", (id_venta,)))
    for r in v["renglones"]:
        r["importe"] = db.de_centavos(r["cantidad"] * r["precioUnitario"])
        r["precioUnitario"] = db.de_centavos(r["precioUnitario"])
    return v


@servicio("ventas.registrar", roles=[EMPLEADO], escritura=True)
def registrar(ctx, lineas, claveOperacion):
    """CU-03, pasos 3 a 9, en una sola transacción atómica (RNF02):
    verifica existencias, guarda la venta con el precio unitario del momento (RFBD04),
    descuenta el stock (RF09, RFBD06), crea los movimientos de salida (RFBD07), registra
    la bitácora (RNF04) e informa los productos que quedaron en stock bajo (RF07).
    Si la conexión se interrumpe y el empleado reintenta, ``claveOperacion`` evita que la
    venta se duplique (excepción 6.1)."""
    clave = db.texto(claveOperacion, "Clave de operación", 64)
    previa = ctx.con.execute("SELECT idVenta FROM venta WHERE claveOperacion = ?", (clave,)).fetchone()
    if previa:
        return _detalle(ctx.con, previa[0]) | {"stockBajo": [], "repetida": True}

    if not isinstance(lineas, list) or not lineas:
        raise ErrorValidacion("Agrega al menos un producto a la venta.")
    cantidades: dict[int, int] = {}
    for linea in lineas:
        if not isinstance(linea, dict):
            raise ErrorValidacion("Renglón de venta mal formado.")
        pid = db.entero(linea.get("idProducto"), "Producto", 1)
        cantidades[pid] = cantidades.get(pid, 0) + db.entero(linea.get("cantidad"), "Cantidad", 1)

    # RFBD05: la venta debe atribuirse a un usuario y una sucursal existentes.
    if not ctx.con.execute("SELECT 1 FROM usuario u JOIN sucursal s ON s.idSucursal = u.idSucursal "
                           "WHERE u.idUsuario = ? AND s.idSucursal = ?", (ctx.id_usuario, ctx.id_sucursal)).fetchone():
        raise ErrorValidacion("El usuario o la sucursal de la venta no existen.")

    precios = {}
    for pid in cantidades:
        f = ctx.con.execute("SELECT precio FROM producto WHERE idProducto = ?", (pid,)).fetchone()
        if not f:
            raise ErrorValidacion("Uno de los productos de la venta ya no existe en el catálogo.")
        precios[pid] = f[0]
    total = sum(precios[pid] * n for pid, n in cantidades.items())

    cur = ctx.con.execute("INSERT INTO venta (fecha, total, idUsuario, idSucursal, claveOperacion) VALUES (?,?,?,?,?)",
                          (db.ahora(), total, ctx.id_usuario, ctx.id_sucursal, clave))
    id_venta = cur.lastrowid
    stock_bajo = []
    for pid, n in cantidades.items():
        ctx.con.execute("INSERT INTO detalleventa (idVenta, idProducto, cantidad, precioUnitario) VALUES (?,?,?,?)",
                        (id_venta, pid, n, precios[pid]))
        r = salida(ctx.con, pid, ctx.id_sucursal, n)  # rechaza si supera existencias -> se revierte todo
        if r["stockBajo"]:
            stock_bajo.append({"idProducto": pid, "nombre": r["nombre"], "existencia": r["existencia"]})
    bitacora(ctx.con, ctx.id_usuario, f"Registrar venta #{id_venta} por {db.de_centavos(total)}", "Venta")
    return _detalle(ctx.con, id_venta) | {"stockBajo": stock_bajo, "repetida": False}


@servicio("ventas.historial", roles=[ADMINISTRADOR])
def historial(ctx, limite=1000):
    """CU-13: historial con fecha, usuario, sucursal y total (RF10, RF11)."""
    limite = max(1, min(10000, db.entero(limite, "Límite", 1)))
    filas = db.filas(ctx.con.execute(
        "SELECT v.idVenta, v.fecha, u.nombre AS usuario, s.nombre AS sucursal, v.total FROM venta v "
        "JOIN usuario u ON u.idUsuario = v.idUsuario JOIN sucursal s ON s.idSucursal = v.idSucursal "
        "ORDER BY v.fecha DESC, v.idVenta DESC LIMIT ?", (limite,)))
    for f in filas:
        f["total"] = db.de_centavos(f["total"])
    return filas


@servicio("ventas.detalle", roles=[ADMINISTRADOR])
def detalle(ctx, idVenta):
    """CU-13 paso 4: productos, cantidades y precio unitario del momento."""
    return _detalle(ctx.con, db.entero(idVenta, "Venta", 1))
