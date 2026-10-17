"""Núcleo compartido: base de datos, seguridad, errores y despachador de servicios.

La lógica de negocio vive separada de la interfaz de usuario (RNF06): los módulos
registran sus servicios aquí y la interfaz solo los invoca a través de una conexión.
"""
