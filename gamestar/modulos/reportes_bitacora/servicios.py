"""Generación de reportes (CU-15) y estadística de productos más vendidos."""

from __future__ import annotations

from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorValidacion
from gamestar.nucleo.reglas import NOMBRE_ESTADO, es_stock_bajo
from gamestar.nucleo.servicios import ADMINISTRADOR, servicio

TIPOS_REPORTE = ("INVENTARIO", "VENTAS", "REPARACIONES")


def _inventario(con):
    sucursales = db.filas(con.execute("SELECT idSucursal, nombre FROM sucursal ORDER BY idSucursal"))
    productos = db.filas(con.execute(
        "SELECT p.idProducto, p.nombre, c.nombre AS categoria, p.stockMinimo FROM producto p "
        "JOIN categoria c ON c.idCategoria = p.idCategoria ORDER BY p.nombre COLLATE NOCASE"))
    existencias = {(r["idProducto"], r["idSucursal"]): r["existencia"]
                   for r in db.filas(con.execute("SELECT idProducto, idSucursal, existencia FROM inventario"))}
    columnas = ["Producto", "Categoría"] + [f"Existencia · {s['nombre']}" for s in sucursales] + ["Stock mínimo", "Estado"]
    filas, bajos = [], 0
    for p in productos:
        exis = [existencias.get((p["idProducto"], s["idSucursal"]), 0) for s in sucursales]
        bajo = any(es_stock_bajo(e, p["stockMinimo"]) for e in exis)
        bajos += bajo
        filas.append([p["nombre"], p["categoria"], *exis, p["stockMinimo"], "Stock bajo" if bajo else "—"])
    resumen = [("Productos", str(len(productos))), ("Con stock bajo", str(bajos)),
               ("Unidades en existencia", str(sum(existencias.values())))]
    return columnas, filas, resumen


def _ventas(con):
    ventas = db.filas(con.execute(
        "SELECT v.idVenta, v.fecha, u.nombre AS usuario, s.nombre AS sucursal, v.total, "
        "(SELECT SUM(cantidad) FROM detalleventa d WHERE d.idVenta = v.idVenta) AS unidades "
        "FROM venta v JOIN usuario u ON u.idUsuario = v.idUsuario JOIN sucursal s ON s.idSucursal = v.idSucursal "
        "ORDER BY v.fecha DESC, v.idVenta DESC"))
    columnas = ["Folio", "Fecha", "Usuario", "Sucursal", "Unidades", "Total"]
    filas = [[v["idVenta"], v["fecha"], v["usuario"], v["sucursal"], v["unidades"] or 0, db.de_centavos(v["total"])]
             for v in ventas]
    total = sum(v["total"] for v in ventas)
    resumen = [("Ventas", str(len(ventas))), ("Unidades vendidas", str(sum(v["unidades"] or 0 for v in ventas))),
               ("Total vendido", db.de_centavos(total))]
    return columnas, filas, resumen


def _reparaciones(con):
    reps = db.filas(con.execute(
        "SELECT r.idReparacion, r.cliente, r.telefono, r.equipo, r.estado, r.fechaIngreso, r.fechaEntrega, "
        "s.nombre AS sucursal FROM reparacion r JOIN sucursal s ON s.idSucursal = r.idSucursal "
        "ORDER BY r.fechaIngreso DESC, r.idReparacion DESC"))
    columnas = ["Folio", "Cliente", "Teléfono", "Equipo", "Estado", "Sucursal", "Ingreso", "Entrega"]
    filas = [[r["idReparacion"], r["cliente"], r["telefono"], r["equipo"], NOMBRE_ESTADO[r["estado"]], r["sucursal"],
              r["fechaIngreso"], r["fechaEntrega"] or "—"] for r in reps]
    conteo = {e: sum(1 for r in reps if r["estado"] == e) for e in NOMBRE_ESTADO}
    resumen = [("Reparaciones", str(len(reps)))] + [(NOMBRE_ESTADO[e], str(n)) for e, n in conteo.items()] + \
              [("Entregadas", str(sum(1 for r in reps if r["fechaEntrega"])))]
    return columnas, filas, resumen


GENERADORES = {"INVENTARIO": _inventario, "VENTAS": _ventas, "REPARACIONES": _reparaciones}


@servicio("reportes.generar", roles=[ADMINISTRADOR], escritura=True)
def generar(ctx, tipo):
    tipo = str(tipo or "").strip().upper()
    if tipo not in TIPOS_REPORTE:
        raise ErrorValidacion("Elige el tipo de reporte: inventario, ventas o reparaciones.")
    columnas, filas, resumen = GENERADORES[tipo](ctx.con)
    fecha = db.ahora()
    # RFBD09: el reporte queda vinculado a quien lo solicitó y a su fecha de generación.
    cur = ctx.con.execute("INSERT INTO reporte (tipo, fechaGeneracion, idUsuario) VALUES (?,?,?)",
                          (tipo, fecha, ctx.id_usuario))
    return {
        "idReporte": cur.lastrowid, "tipo": tipo, "fechaGeneracion": fecha, "solicitadoPor": ctx.usuario["nombre"],
        "columnas": columnas, "filas": filas, "resumen": resumen,
        # Flujo alterno 3.1 del CU-15: sin datos se genera el reporte vacío con un aviso.
        "aviso": None if filas else "No hay datos registrados para este tipo de reporte.",
    }


@servicio("reportes.mas_vendidos", roles=[ADMINISTRADOR])
def mas_vendidos(ctx, limite=10):
    limite = max(1, min(100, db.entero(limite, "Límite", 1)))
    return db.filas(ctx.con.execute(
        "SELECT p.idProducto, p.nombre, c.nombre AS categoria, SUM(d.cantidad) AS unidades "
        "FROM detalleventa d JOIN producto p ON p.idProducto = d.idProducto "
        "JOIN categoria c ON c.idCategoria = p.idCategoria "
        "GROUP BY p.idProducto ORDER BY unidades DESC, p.nombre COLLATE NOCASE LIMIT ?", (limite,)))
