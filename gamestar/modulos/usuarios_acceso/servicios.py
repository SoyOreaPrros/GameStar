"""Lógica de negocio de usuarios y acceso."""

from __future__ import annotations

from gamestar.nucleo import db, seguridad
from gamestar.nucleo.errores import ErrorValidacion
from gamestar.nucleo.servicios import ADMINISTRADOR, AMBOS, EMPLEADO, servicio

ROLES = (EMPLEADO, ADMINISTRADOR)  # RFBD02


def _usuario_publico(con, id_usuario: int) -> dict:
    return db.fila(con.execute(
        "SELECT u.idUsuario, u.nombre, u.usuarioAcceso, u.rol, u.idSucursal, s.nombre AS sucursal "
        "FROM usuario u JOIN sucursal s ON s.idSucursal = u.idSucursal WHERE u.idUsuario = ?", (id_usuario,)))


def _validar_sucursal(con, id_sucursal) -> int:
    id_sucursal = db.entero(id_sucursal, "Sucursal", 1)
    if not con.execute("SELECT 1 FROM sucursal WHERE idSucursal = ?", (id_sucursal,)).fetchone():
        raise ErrorValidacion("Sucursal: selecciona una sucursal registrada.")
    return id_sucursal


def _validar_rol(rol) -> str:
    rol = str(rol or "").strip().upper()
    if rol not in ROLES:
        raise ErrorValidacion("Rol: solo se permite empleado o administrador.")
    return rol


def _validar_acceso_unico(con, usuario_acceso: str, excepto: int | None = None):
    fila = con.execute("SELECT idUsuario FROM usuario WHERE usuarioAcceso = ? COLLATE NOCASE", (usuario_acceso,)).fetchone()
    if fila and fila[0] != excepto:
        raise ErrorValidacion("El usuario de acceso ya existe. Elige otro.")


def _datos_usuario(con, nombre, usuario_acceso, id_sucursal):
    nombre = db.texto(nombre, "Nombre", 100)
    usuario_acceso = db.texto(usuario_acceso, "Usuario de acceso", 30)
    if any(c.isspace() for c in usuario_acceso):
        raise ErrorValidacion("Usuario de acceso: no debe contener espacios.")
    return nombre, usuario_acceso, _validar_sucursal(con, id_sucursal)


# ---------------------------------------------------------------------------
# Acceso (CU-01)
# ---------------------------------------------------------------------------
@servicio("usuarios.estado_inicial", publico=True)
def estado_inicial(ctx):
    """Indica si ya existe algún usuario (para la configuración del primer administrador)."""
    hay = ctx.con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] > 0
    return {"hay_usuarios": hay, "sucursales": sucursales(ctx)}


@servicio("usuarios.crear_administrador_inicial", publico=True, escritura=True)
def crear_administrador_inicial(ctx, nombre, usuarioAcceso, contrasena, idSucursal):
    """Solo funciona cuando todavía no hay usuarios: crea la cuenta del dueño del local."""
    if ctx.con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] > 0:
        raise ErrorValidacion("El sistema ya tiene usuarios registrados.")
    nombre, usuarioAcceso, idSucursal = _datos_usuario(ctx.con, nombre, usuarioAcceso, idSucursal)
    contrasena = db.texto(contrasena, "Contraseña", 255)
    cur = ctx.con.execute("INSERT INTO usuario (nombre, usuarioAcceso, contrasena, rol, idSucursal) VALUES (?,?,?,?,?)",
                          (nombre, usuarioAcceso, seguridad.cifrar(contrasena), ADMINISTRADOR, idSucursal))
    return _usuario_publico(ctx.con, cur.lastrowid)


@servicio("usuarios.iniciar_sesion", publico=True)
def iniciar_sesion(ctx, usuarioAcceso, contrasena):
    fila = db.fila(ctx.con.execute("SELECT idUsuario, contrasena FROM usuario WHERE usuarioAcceso = ? COLLATE NOCASE",
                                   (str(usuarioAcceso or "").strip(),)))
    if not fila or not seguridad.verificar(str(contrasena or ""), fila["contrasena"]):
        raise ErrorValidacion("Las credenciales ingresadas no son válidas.")  # excepción 4.1 del CU-01
    usuario = _usuario_publico(ctx.con, fila["idUsuario"])
    return {"token": ctx.abrir_sesion(usuario["idUsuario"]), "usuario": usuario}


@servicio("usuarios.cerrar_sesion")
def cerrar_sesion(ctx):
    ctx.cerrar_sesion()
    return True


@servicio("usuarios.sucursales", publico=True)
def sucursales(ctx):
    return db.filas(ctx.con.execute("SELECT idSucursal, nombre FROM sucursal ORDER BY idSucursal"))


# ---------------------------------------------------------------------------
# Administración de usuarios (CU-10, CU-11, CU-12)
# ---------------------------------------------------------------------------
@servicio("usuarios.listar", roles=[ADMINISTRADOR])
def listar(ctx):
    return db.filas(ctx.con.execute(
        "SELECT u.idUsuario, u.nombre, u.usuarioAcceso, u.rol, u.idSucursal, s.nombre AS sucursal "
        "FROM usuario u JOIN sucursal s ON s.idSucursal = u.idSucursal ORDER BY u.nombre COLLATE NOCASE"))


@servicio("usuarios.registrar", roles=[ADMINISTRADOR], escritura=True)
def registrar(ctx, nombre, usuarioAcceso, contrasena, rol, idSucursal):
    nombre, usuarioAcceso, idSucursal = _datos_usuario(ctx.con, nombre, usuarioAcceso, idSucursal)
    contrasena = db.texto(contrasena, "Contraseña", 255)
    rol = _validar_rol(rol)
    _validar_acceso_unico(ctx.con, usuarioAcceso)  # excepción 3.1 del CU-10
    cur = ctx.con.execute("INSERT INTO usuario (nombre, usuarioAcceso, contrasena, rol, idSucursal) VALUES (?,?,?,?,?)",
                          (nombre, usuarioAcceso, seguridad.cifrar(contrasena), rol, idSucursal))
    return _usuario_publico(ctx.con, cur.lastrowid)


def _existente(con, id_usuario) -> dict:
    u = _usuario_publico(con, db.entero(id_usuario, "Usuario", 1))
    if not u:
        raise ErrorValidacion("El usuario seleccionado no existe.")
    return u


@servicio("usuarios.modificar", roles=[ADMINISTRADOR], escritura=True)
def modificar(ctx, idUsuario, nombre, usuarioAcceso, idSucursal, contrasena=""):
    """CU-11: nombre, usuario de acceso, contraseña (opcional) o sucursal."""
    u = _existente(ctx.con, idUsuario)
    nombre, usuarioAcceso, idSucursal = _datos_usuario(ctx.con, nombre, usuarioAcceso, idSucursal)
    _validar_acceso_unico(ctx.con, usuarioAcceso, excepto=u["idUsuario"])  # excepción 3.1 del CU-11
    ctx.con.execute("UPDATE usuario SET nombre = ?, usuarioAcceso = ?, idSucursal = ? WHERE idUsuario = ?",
                    (nombre, usuarioAcceso, idSucursal, u["idUsuario"]))
    if str(contrasena or "").strip():
        ctx.con.execute("UPDATE usuario SET contrasena = ? WHERE idUsuario = ?",
                        (seguridad.cifrar(db.texto(contrasena, "Contraseña", 255)), u["idUsuario"]))
    return _usuario_publico(ctx.con, u["idUsuario"])


@servicio("usuarios.asignar_rol", roles=[ADMINISTRADOR], escritura=True)
def asignar_rol(ctx, idUsuario, rol):
    u = _existente(ctx.con, idUsuario)
    rol = _validar_rol(rol)  # excepción 3.1 del CU-12
    if u["rol"] == ADMINISTRADOR and rol != ADMINISTRADOR:
        admins = ctx.con.execute("SELECT COUNT(*) FROM usuario WHERE rol = ?", (ADMINISTRADOR,)).fetchone()[0]
        if admins <= 1:
            raise ErrorValidacion("Debe quedar al menos un administrador en el sistema.")
    ctx.con.execute("UPDATE usuario SET rol = ? WHERE idUsuario = ?", (rol, u["idUsuario"]))
    return _usuario_publico(ctx.con, u["idUsuario"])
