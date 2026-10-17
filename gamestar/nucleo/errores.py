"""Errores que la lógica de negocio comunica a la interfaz."""


class ErrorGameStar(Exception):
    """Error base. Su mensaje se muestra tal cual al usuario."""

    tipo = "error"

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ErrorValidacion(ErrorGameStar):
    """Datos capturados que no cumplen las reglas (excepciones de los CU)."""

    tipo = "validacion"


class ErrorPermiso(ErrorGameStar):
    """El rol de la sesión no permite la función solicitada (RNF03)."""

    tipo = "permiso"


class ErrorSesion(ErrorGameStar):
    """No hay sesión activa o expiró."""

    tipo = "sesion"


class ErrorConexion(ErrorGameStar):
    """No fue posible comunicarse con el servidor (RNF02)."""

    tipo = "conexion"


TIPOS = {c.tipo: c for c in (ErrorGameStar, ErrorValidacion, ErrorPermiso, ErrorSesion, ErrorConexion)}
