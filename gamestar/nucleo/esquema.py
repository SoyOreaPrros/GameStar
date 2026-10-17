"""Esquema de la base de datos central, derivado del diagrama de clases (2.3.1)
y del diccionario de datos (2.3.2) del documento PRY03.

Desviaciones documentadas respecto al diccionario de datos:
- Los importes (precio, total, precioUnitario) se guardan en centavos (INTEGER)
  porque SQLite no tiene tipo DECIMAL; la aplicación los expone con formato 0.00.
- Reparacion.telefono: atiende el resultado 3 de la evaluación del prototipo (2.2.3)
  y el campo "Teléfono de contacto del cliente" del diseño final.
- Venta.claveOperacion: clave única por operación para que, si se interrumpe la
  conexión, reintentar la venta no la duplique (RNF02, excepción 6.1 del CU-03).
"""

from __future__ import annotations

from .db import conectar

DDL = """
CREATE TABLE IF NOT EXISTS sucursal (
    idSucursal  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL CHECK (length(nombre) BETWEEN 1 AND 60)
);

CREATE TABLE IF NOT EXISTS usuario (
    idUsuario     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL CHECK (length(nombre) BETWEEN 1 AND 100),
    usuarioAcceso TEXT    NOT NULL UNIQUE COLLATE NOCASE CHECK (length(usuarioAcceso) BETWEEN 1 AND 30),
    contrasena    TEXT    NOT NULL CHECK (length(contrasena) <= 255),
    rol           TEXT    NOT NULL CHECK (rol IN ('EMPLEADO', 'ADMINISTRADOR')),        -- RFBD02
    idSucursal    INTEGER NOT NULL REFERENCES sucursal (idSucursal)
);

CREATE TABLE IF NOT EXISTS categoria (
    idCategoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE CHECK (length(nombre) BETWEEN 1 AND 50)
);

CREATE TABLE IF NOT EXISTS producto (
    idProducto  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL CHECK (length(nombre) BETWEEN 1 AND 100),
    precio      INTEGER NOT NULL CHECK (precio > 0),                 -- centavos
    stockMinimo INTEGER NOT NULL CHECK (stockMinimo >= 0),
    idCategoria INTEGER NOT NULL REFERENCES categoria (idCategoria)
);

CREATE TABLE IF NOT EXISTS inventario (                               -- RFBD03
    idInventario INTEGER PRIMARY KEY AUTOINCREMENT,
    idProducto   INTEGER NOT NULL REFERENCES producto (idProducto),
    idSucursal   INTEGER NOT NULL REFERENCES sucursal (idSucursal),
    existencia   INTEGER NOT NULL CHECK (existencia >= 0),
    UNIQUE (idProducto, idSucursal)
);

CREATE TABLE IF NOT EXISTS movimientoinventario (                     -- RFBD07
    idMovimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    idInventario INTEGER NOT NULL REFERENCES inventario (idInventario),
    tipo         TEXT    NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA')),
    cantidad     INTEGER NOT NULL CHECK (cantidad > 0),
    fecha        TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS venta (
    idVenta        INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha          TEXT    NOT NULL,
    total          INTEGER NOT NULL CHECK (total >= 0),             -- centavos
    idUsuario      INTEGER NOT NULL REFERENCES usuario (idUsuario),  -- RFBD05
    idSucursal     INTEGER NOT NULL REFERENCES sucursal (idSucursal),-- RFBD05
    claveOperacion TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS detalleventa (
    idDetalleVenta INTEGER PRIMARY KEY AUTOINCREMENT,
    idVenta        INTEGER NOT NULL REFERENCES venta (idVenta),
    idProducto     INTEGER NOT NULL REFERENCES producto (idProducto),
    cantidad       INTEGER NOT NULL CHECK (cantidad > 0),
    precioUnitario INTEGER NOT NULL CHECK (precioUnitario >= 0)      -- RFBD04, centavos
);

CREATE TABLE IF NOT EXISTS reparacion (
    idReparacion INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente      TEXT    NOT NULL CHECK (length(cliente) BETWEEN 1 AND 100),
    telefono     TEXT    NOT NULL CHECK (length(telefono) BETWEEN 1 AND 20),
    equipo       TEXT    NOT NULL CHECK (length(equipo) BETWEEN 1 AND 100),
    falla        TEXT    NOT NULL CHECK (length(falla) BETWEEN 1 AND 500),
    estado       TEXT    NOT NULL CHECK (estado IN ('PENDIENTE', 'EN_PROCESO', 'TERMINADA')),  -- RFBD10
    fechaIngreso TEXT    NOT NULL,
    fechaEntrega TEXT,
    idUsuario    INTEGER NOT NULL REFERENCES usuario (idUsuario),
    idSucursal   INTEGER NOT NULL REFERENCES sucursal (idSucursal)
);

CREATE TABLE IF NOT EXISTS refaccionusada (                           -- RFBD08
    idRefaccionUsada INTEGER PRIMARY KEY AUTOINCREMENT,
    idReparacion     INTEGER NOT NULL REFERENCES reparacion (idReparacion),
    idProducto       INTEGER NOT NULL REFERENCES producto (idProducto),
    cantidad         INTEGER NOT NULL CHECK (cantidad > 0)
);

CREATE TABLE IF NOT EXISTS reporte (                                  -- RFBD09
    idReporte       INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('INVENTARIO', 'VENTAS', 'REPARACIONES')),
    fechaGeneracion TEXT    NOT NULL,
    idUsuario       INTEGER NOT NULL REFERENCES usuario (idUsuario)
);

CREATE TABLE IF NOT EXISTS bitacora (                                 -- RNF04
    idBitacora INTEGER PRIMARY KEY AUTOINCREMENT,
    idUsuario  INTEGER NOT NULL REFERENCES usuario (idUsuario),
    accion     TEXT    NOT NULL CHECK (length(accion) BETWEEN 1 AND 100),
    entidad    TEXT    NOT NULL CHECK (length(entidad) BETWEEN 1 AND 50),
    fecha      TEXT    NOT NULL
);

-- Bitácora inalterable (RNF04): no se permite modificar ni borrar registros.
CREATE TRIGGER IF NOT EXISTS bitacora_sin_cambios BEFORE UPDATE ON bitacora
BEGIN SELECT RAISE(ABORT, 'La bitácora es inalterable'); END;
CREATE TRIGGER IF NOT EXISTS bitacora_sin_borrado BEFORE DELETE ON bitacora
BEGIN SELECT RAISE(ABORT, 'La bitácora es inalterable'); END;

-- Índices para respuestas rápidas en consultas de mostrador (RNF01).
CREATE INDEX IF NOT EXISTS ix_producto_nombre   ON producto (nombre);
CREATE INDEX IF NOT EXISTS ix_inventario_suc    ON inventario (idSucursal);
CREATE INDEX IF NOT EXISTS ix_mov_inventario    ON movimientoinventario (idInventario);
CREATE INDEX IF NOT EXISTS ix_detalle_venta     ON detalleventa (idVenta);
CREATE INDEX IF NOT EXISTS ix_detalle_producto  ON detalleventa (idProducto);
CREATE INDEX IF NOT EXISTS ix_refaccion_rep     ON refaccionusada (idReparacion);
CREATE INDEX IF NOT EXISTS ix_reparacion_estado ON reparacion (estado);
"""

# Datos base que el documento establece:
# - "Sucursal: punto de venta de GameStar; el negocio opera dos." (nombres de ejemplo
#   del diccionario de datos: "Sucursal 1").
# - Categorías de ejemplo del catálogo: Videojuegos, Consolas y Accesorios.
SUCURSALES_BASE = ("Sucursal 1", "Sucursal 2")
CATEGORIAS_BASE = ("Videojuegos", "Consolas", "Accesorios")


def inicializar(ruta: str) -> None:
    """Crea las tablas si no existen y carga los datos base una sola vez."""
    con = conectar(ruta)
    try:
        con.execute("PRAGMA journal_mode = WAL")
        con.executescript(DDL)
        con.execute("BEGIN")
        if con.execute("SELECT COUNT(*) FROM sucursal").fetchone()[0] == 0:
            con.executemany("INSERT INTO sucursal (nombre) VALUES (?)", [(n,) for n in SUCURSALES_BASE])
        if con.execute("SELECT COUNT(*) FROM categoria").fetchone()[0] == 0:
            con.executemany("INSERT INTO categoria (nombre) VALUES (?)", [(n,) for n in CATEGORIAS_BASE])
        con.execute("COMMIT")
    finally:
        con.close()
