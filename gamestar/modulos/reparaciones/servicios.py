"""Lógica de negocio de reparaciones.

Las reparaciones no se borran: el historial se conserva (resultado 4 de la evaluación
del prototipo pide mantenerlo al menos una semana).
"""

from __future__ import annotations

from datetime import datetime

from gamestar.modulos.inventario.servicios import normalizar, salida
from gamestar.modulos.reportes_bitacora.bitacora import registrar as bitacora
from gamestar.nucleo import db
from gamestar.nucleo.errores import ErrorValidacion
from gamestar.nucleo.reglas import ESTADOS_REPARACION, NOMBRE_ESTADO
from gamestar.nucleo.servicios import ADMINISTRADOR, AMBOS, EMPLEADO, servicio

CAMPOS = ("r.idReparacion, r.cliente, r.telefono, r.equipo, r.falla, r.estado, r.fechaIngreso, r.fechaEntrega, "
          "r.idUsuario, u.nombre AS usuario, r.idSucursal, s.nombre AS sucursal")
DESDE = "FROM reparacion r JOIN usuario u ON u.idUsuario = r.idUsuario JOIN sucursal s ON s.idSucursal = r.idSucursal"


def _con_nombre_estado(r: dict) -> dict:
    r["nombreEstado"] = NOMBRE_ESTADO[r["estado"]]
    return r


def _reparacion(con, id_reparacion) -> dict:
    r = db.fila(con.execute(f"SELECT {CAMPOS} {DESDE} WHERE r.idReparacion = ?",
                            (db.entero(id_reparacion, "Reparación", 1),)))
    if not r:
        raise ErrorValidacion("La reparación seleccionada no existe.")
    r["refacciones"] = db.filas(con.execute(
        "SELECT ru.idRefaccionUsada, ru.idProducto, p.nombre, ru.cantidad FROM refaccionusada ru "
        "JOIN producto p ON p.idProducto = ru.idProducto WHERE ru.idReparacion = ? ORDER BY ru.idRefaccionUsada",
        (r["idReparacion"],)))
    return _con_nombre_estado(r)


@servicio("reparaciones.registrar", roles=[EMPLEADO], escritura=True)
def registrar(ctx, cliente, telefono, equipo, falla):
    """CU-04: datos del cliente (RF13), teléfono de contacto, equipo recibido (RF14) y falla
    reportada. Se guarda en estado PENDIENTE con su fecha de ingreso, ligada al usuario y a
    la sucursal."""
    faltan = [n for n, v in (("Datos del cliente", cliente), ("Teléfono de contacto", telefono),
                             ("Datos del equipo", equipo), ("Diagnóstico o falla", falla)) if not str(v or "").strip()]
    if faltan:  # excepción 5.1 del CU-04
        raise ErrorValidacion("Faltan datos obligatorios: " + ", ".join(faltan) + ".")
    cliente = db.texto(cliente, "Datos del cliente", 100)
    telefono = db.texto(telefono, "Teléfono de contacto", 20)
    equipo = db.texto(equipo, "Datos del equipo", 100)
    falla = db.texto(falla, "Diagnóstico o falla", 500)
    cur = ctx.con.execute(
        "INSERT INTO reparacion (cliente, telefono, equipo, falla, estado, fechaIngreso, idUsuario, idSucursal) "
        "VALUES (?,?,?,?,?,?,?,?)", (cliente, telefono, equipo, falla, "PENDIENTE", db.ahora(), ctx.id_usuario,
                                     ctx.id_sucursal))
    bitacora(ctx.con, ctx.id_usuario, f"Registrar reparación #{cur.lastrowid}", "Reparacion")
    return _reparacion(ctx.con, cur.lastrowid)


@servicio("reparaciones.buscar", roles=AMBOS)
def buscar(ctx, texto="", limite=20):
    """Localizar una reparación por folio, cliente, teléfono o equipo (CU-05 y CU-06, paso 1)."""
    filas = [_con_nombre_estado(r) for r in db.filas(ctx.con.execute(
        f"SELECT {CAMPOS} {DESDE} ORDER BY r.fechaIngreso DESC, r.idReparacion DESC"))]
    buscado = normalizar(texto)
    if buscado.startswith("#"):  # búsqueda por folio
        filas = [r for r in filas if buscado[1:].strip() == str(r["idReparacion"])]
    elif buscado:
        filas = [r for r in filas if buscado == str(r["idReparacion"]) or
                 any(buscado in normalizar(r[c]) for c in ("cliente", "telefono", "equipo"))]
    return filas[:max(1, min(200, db.entero(limite, "Límite", 1)))]


@servicio("reparaciones.obtener", roles=AMBOS)
def obtener(ctx, idReparacion):
    return _reparacion(ctx.con, idReparacion)


@servicio("reparaciones.listar", roles=[ADMINISTRADOR])
def listar(ctx):
    """CU-14: reparaciones con cliente, teléfono, equipo, estado y fechas."""
    return [_con_nombre_estado(r) for r in db.filas(ctx.con.execute(
        f"SELECT {CAMPOS} {DESDE} ORDER BY r.fechaIngreso DESC, r.idReparacion DESC"))]


@servicio("reparaciones.actualizar_estado", roles=[EMPLEADO], escritura=True)
def actualizar_estado(ctx, idReparacion, estado):
    """CU-05 / RF15: solo estados reconocidos (RFBD10); queda en la bitácora (RNF04)."""
    r = _reparacion(ctx.con, idReparacion)
    estado = str(estado or "").strip().upper()
    if estado not in ESTADOS_REPARACION:  # excepción 3.1
        raise ErrorValidacion("Estado no reconocido: elige pendiente, en proceso o terminada.")
    ctx.con.execute("UPDATE reparacion SET estado = ? WHERE idReparacion = ?", (estado, r["idReparacion"]))
    bitacora(ctx.con, ctx.id_usuario,
             f"Cambiar estado de reparación #{r['idReparacion']}: {r['estado']} -> {estado}", "Reparacion")
    return _reparacion(ctx.con, r["idReparacion"])


@servicio("reparaciones.refacciones_disponibles", roles=[EMPLEADO])
def refacciones_disponibles(ctx, idReparacion, texto=""):
    """Productos con existencia en la sucursal que recibió el equipo."""
    r = _reparacion(ctx.con, idReparacion)
    filas = db.filas(ctx.con.execute(
        "SELECT p.idProducto, p.nombre, i.existencia FROM inventario i JOIN producto p ON p.idProducto = i.idProducto "
        "WHERE i.idSucursal = ? AND i.existencia > 0 ORDER BY p.nombre COLLATE NOCASE", (r["idSucursal"],)))
    buscado = normalizar(texto)
    return [f for f in filas if buscado in normalizar(f["nombre"])] if buscado else filas


@servicio("reparaciones.registrar_refaccion", roles=[EMPLEADO], escritura=True)
def registrar_refaccion(ctx, idReparacion, idProducto, cantidad):
    """Flujo alterno 2.1 del CU-05: la pieza usada se descuenta del inventario de la sucursal
    de la reparación (RFBD08) y genera su movimiento de salida (RFBD07)."""
    r = _reparacion(ctx.con, idReparacion)
    pid = db.entero(idProducto, "Producto", 1)
    cantidad = db.entero(cantidad, "Cantidad", 1)
    resultado = salida(ctx.con, pid, r["idSucursal"], cantidad)  # valida producto y existencias
    ctx.con.execute("INSERT INTO refaccionusada (idReparacion, idProducto, cantidad) VALUES (?,?,?)",
                    (r["idReparacion"], pid, cantidad))
    bitacora(ctx.con, ctx.id_usuario, f"Refacción usada en reparación #{r['idReparacion']}: "
                                      f"{cantidad} u. de producto #{pid}", "Inventario")
    return _reparacion(ctx.con, r["idReparacion"]) | {"existenciaRestante": resultado["existencia"],
                                                        "stockBajo": resultado["stockBajo"]}


def _fecha(valor) -> str:
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).strftime(db.FORMATO_FECHA)
        except ValueError:
            pass
    raise ErrorValidacion("Fecha de entrega: usa el formato dd/mm/aaaa.")


@servicio("reparaciones.registrar_entrega", roles=[EMPLEADO], escritura=True)
def registrar_entrega(ctx, idReparacion, fechaEntrega):
    """CU-06 / RF17: solo se registra la entrega si la reparación está terminada."""
    r = _reparacion(ctx.con, idReparacion)
    if r["estado"] != "TERMINADA":  # excepción 1.1
        raise ErrorValidacion("La entrega solo se registra si la reparación está terminada.")
    fecha = _fecha(fechaEntrega)
    ctx.con.execute("UPDATE reparacion SET fechaEntrega = ? WHERE idReparacion = ?", (fecha, r["idReparacion"]))
    bitacora(ctx.con, ctx.id_usuario, f"Registrar entrega de reparación #{r['idReparacion']} ({fecha})", "Reparacion")
    return _reparacion(ctx.con, r["idReparacion"])
