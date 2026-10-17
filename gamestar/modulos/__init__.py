"""Módulos funcionales del sistema. Cada uno se desarrolla en su propia rama:

    usuarios_acceso    -> feature/usuarios-acceso
    reportes_bitacora  -> feature/reportes-bitacora
    inventario         -> feature/inventario
    ventas             -> feature/ventas
    reparaciones       -> feature/reparaciones

Cada módulo contiene ``servicios.py`` (lógica de negocio) y ``pantallas.py``
(interfaz). El núcleo los descubre automáticamente, así que integrar una rama
solo agrega su carpeta.
"""
