"""Pantallas de acceso (2.2.2.B) y de gestión de usuarios (menú del administrador)."""

from __future__ import annotations

import tkinter as tk

from gamestar import SUBTITULO_SISTEMA
from gamestar.ui import tema as t
from gamestar.ui import widgets as w
from gamestar.ui.app import (NOMBRE_ROL, ROL_ADMINISTRADOR, ROL_EMPLEADO, SOLO_ADMIN, Dialogo, Pantalla,
                             TarjetaMenu)
from gamestar.nucleo.errores import ErrorGameStar


class InicioSesion(Pantalla):
    """CU-01. Muestra el aviso "Acceso denegado" cuando las credenciales no son válidas
    (excepción 4.1) y permite intentar de nuevo. Si todavía no existe ningún usuario,
    solicita crear la cuenta del administrador (dueño del local)."""

    con_encabezado = False

    def construir(self, denegado=False):
        centro = tk.Frame(self, bg=t.FONDO)
        centro.place(relx=0.5, rely=0.47, anchor="center")
        self.tarjeta = w.Tarjeta(centro, padx=44, pady=40, radio=14, modo="contenido")
        self.tarjeta.pack()
        c = self.tarjeta.cuerpo
        tk.Label(c, image=self.app.logo_login, bg=t.BLANCO, bd=0).pack(pady=(4, 10))
        w.etiqueta(c, SUBTITULO_SISTEMA, "dato", color=t.TEXTO_TENUE, bg=t.BLANCO).pack(pady=(0, 24))
        self.zona_error = tk.Frame(c, bg=t.BLANCO)
        self.zona_error.pack(fill="x")
        self.formulario = tk.Frame(c, bg=t.BLANCO, width=388)
        self.formulario.pack(fill="x")
        try:
            estado = self.app.conexion.llamar("usuarios.estado_inicial")
        except ErrorGameStar as e:
            self._sin_servidor(e.mensaje)
            return
        if estado["hay_usuarios"]:
            self._formulario_acceso()
            if denegado:
                self.mostrar_error()
        else:
            self._formulario_inicial(estado["sucursales"])

    # -- acceso -------------------------------------------------------------
    def _formulario_acceso(self):
        f = self.formulario
        self.usuario = w.campo_con_titulo(f, "Usuario", lambda m: w.Campo(m, "Usuario", ancho=388), pady=(0, 20))
        self.contrasena = w.campo_con_titulo(f, "Contraseña", lambda m: w.Campo(m, "Contraseña", oculto=True), pady=(0, 26))
        w.Boton(f, "Iniciar sesión", self.entrar, ancho=388).pack(fill="x")
        for campo in (self.usuario, self.contrasena):
            campo.al_enter(self.entrar)
        self.after(50, self.usuario.enfocar)

    def mostrar_error(self, titulo="Acceso denegado", texto="Las credenciales ingresadas no son válidas."):
        for hijo in self.zona_error.winfo_children():
            hijo.destroy()
        caja = w.Tarjeta(self.zona_error, padx=16, pady=12, radio=8, relleno=t.ROJO_SUAVE, borde=t.ROJO)
        caja.pack(fill="x", pady=(0, 22))
        w.icono(caja.cuerpo, "error", tam=22, color=t.ROJO_TEXTO).pack(side="left", anchor="n", padx=(0, 12), pady=(1, 0))
        textos = tk.Frame(caja.cuerpo, bg=t.ROJO_SUAVE)
        textos.pack(side="left", fill="x")
        w.etiqueta(textos, titulo, "cuerpo_negrita", color=t.ROJO_TEXTO, bg=t.ROJO_SUAVE).pack(anchor="w")
        w.etiqueta(textos, texto, "cuerpo", color=t.ROJO_TEXTO, bg=t.ROJO_SUAVE).pack(anchor="w")

    def entrar(self):
        try:
            sesion = self.app.conexion.llamar("usuarios.iniciar_sesion", usuarioAcceso=self.usuario.valor(),
                                              contrasena=self.contrasena.valor())
        except ErrorGameStar as e:
            if e.tipo == "conexion":
                self.mostrar_error("Sin conexión", e.mensaje)
            else:
                self.mostrar_error()
                self.contrasena.limpiar()
                self.contrasena.enfocar()
            return
        self.app.iniciar_sesion(sesion)

    # -- primer uso ---------------------------------------------------------
    def _formulario_inicial(self, sucursales):
        f = self.formulario
        w.etiqueta(f, "Configuración inicial", "seccion", bg=t.BLANCO).pack(anchor="w")
        w.etiqueta(f, "Crea la cuenta del administrador (dueño del local).", "tenue", bg=t.BLANCO).pack(anchor="w", pady=(2, 18))
        self.nombre = w.campo_con_titulo(f, "Nombre", lambda m: w.Campo(m, "Nombre completo", ancho=388))
        self.usuario = w.campo_con_titulo(f, "Usuario de acceso", lambda m: w.Campo(m, "Usuario de acceso"))
        self.contrasena = w.campo_con_titulo(f, "Contraseña", lambda m: w.Campo(m, "Contraseña", oculto=True))
        opciones = [(s["idSucursal"], s["nombre"]) for s in sucursales]
        self.sucursal = w.campo_con_titulo(f, "Sucursal", lambda m: w.Selector(m, opciones), pady=(0, 24))
        if opciones:
            self.sucursal.current(0)
        w.Boton(f, "Crear administrador", self.crear_admin).pack(fill="x")

    def crear_admin(self):
        try:
            self.app.conexion.llamar("usuarios.crear_administrador_inicial", nombre=self.nombre.valor(),
                                     usuarioAcceso=self.usuario.valor(), contrasena=self.contrasena.valor(),
                                     idSucursal=self.sucursal.valor())
        except ErrorGameStar as e:
            self.mostrar_error("No se pudo crear", e.mensaje)
            return
        self.app.aviso("Administrador creado. Ya puedes iniciar sesión.")
        self.app.mostrar("login")

    def _sin_servidor(self, mensaje):
        self.mostrar_error("Sin conexión", mensaje)
        w.Boton(self.formulario, "Reintentar", lambda: self.app.mostrar("login"), ancho=388).pack(fill="x")


# ---------------------------------------------------------------------------
class GestionUsuarios(Pantalla):
    """Registrar (CU-10), modificar (CU-11) y asignar rol (CU-12)."""

    titulo = "Gestionar usuarios"
    roles = (ROL_ADMINISTRADOR,)

    def construir(self):
        self.sucursales = self.llamar("usuarios.sucursales") or []
        izq, der = w.columnas_tarjetas(self, (782, 510), margen=(35, 26, 35, 26))
        w.titulo_tarjeta(izq, "Usuarios registrados", "Modificar los datos de acceso o asignar un rol.")
        self.tabla = w.Tabla(izq, [("Nombre", 19), ("Usuario de acceso", 22), ("Rol", 18), ("Sucursal", 15), ("Acciones", 30)],
                             vacio="No hay usuarios registrados.")
        self.tabla.pack(fill="both", expand=True)

        w.titulo_tarjeta(der, "Registrar usuario", "Alta de un usuario con su rol y sucursal.")
        self.nombre = w.campo_con_titulo(der, "Nombre", lambda m: w.Campo(m, "Nombre"))
        self.acceso = w.campo_con_titulo(der, "Usuario de acceso", lambda m: w.Campo(m, "Usuario de acceso"))
        self.contrasena = w.campo_con_titulo(der, "Contraseña", lambda m: w.Campo(m, "Contraseña", oculto=True))
        fila = tk.Frame(der, bg=t.BLANCO)
        fila.pack(fill="x")
        fila.columnconfigure(0, weight=1, uniform="f")
        fila.columnconfigure(1, weight=1, uniform="f")
        roles = [(ROL_EMPLEADO, "Empleado"), (ROL_ADMINISTRADOR, "Administrador")]
        suc = [(s["idSucursal"], s["nombre"]) for s in self.sucursales]
        c1, c2 = tk.Frame(fila, bg=t.BLANCO), tk.Frame(fila, bg=t.BLANCO)
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 9))
        c2.grid(row=0, column=1, sticky="ew", padx=(9, 0))
        self.rol = w.campo_con_titulo(c1, "Rol", lambda m: w.Selector(m, roles, width=10))
        self.sucursal = w.campo_con_titulo(c2, "Sucursal", lambda m: w.Selector(m, suc, width=10))
        self.rol.current(0)
        if suc:
            self.sucursal.current(0)
        w.Boton(der, "Guardar usuario", self.registrar).pack(side="bottom", fill="x")
        self.cargar()

    def cargar(self):
        usuarios = self.llamar("usuarios.listar") or []
        filas = []
        for u in usuarios:
            def acciones(padre, u=u):
                f = tk.Frame(padre, bg=padre.cget("bg"))
                w.enlace(f, "Modificar", lambda: self.modificar(u)).pack(side="left", padx=(0, 18))
                w.enlace(f, "Asignar rol", lambda: self.asignar_rol(u)).pack(side="left")
                return f
            filas.append([u["nombre"], u["usuarioAcceso"], NOMBRE_ROL[u["rol"]], u["sucursal"], acciones])
        self.tabla.cargar(filas, usuarios)

    def registrar(self):
        r = self.llamar("usuarios.registrar", nombre=self.nombre.valor(), usuarioAcceso=self.acceso.valor(),
                        contrasena=self.contrasena.valor(), rol=self.rol.valor(), idSucursal=self.sucursal.valor())
        if r:
            for campo in (self.nombre, self.acceso, self.contrasena):
                campo.limpiar()
            self.app.aviso(f"Usuario «{r['usuarioAcceso']}» registrado.")
            self.cargar()

    def modificar(self, u):
        d = Dialogo(self.app, "Modificar usuario")
        nombre = w.campo_con_titulo(d.cuerpo, "Nombre", lambda m: w.Campo(m, "Nombre", valor=u["nombre"], ancho=420))
        acceso = w.campo_con_titulo(d.cuerpo, "Usuario de acceso", lambda m: w.Campo(m, "Usuario de acceso", valor=u["usuarioAcceso"]))
        contrasena = w.campo_con_titulo(d.cuerpo, "Contraseña nueva", lambda m: w.Campo(m, "Dejar vacío para conservarla", oculto=True))
        suc = [(s["idSucursal"], s["nombre"]) for s in self.sucursales]
        sucursal = w.campo_con_titulo(d.cuerpo, "Sucursal", lambda m: w.Selector(m, suc))
        sucursal.seleccionar(u["idSucursal"])

        def guardar():
            r = self.llamar("usuarios.modificar", idUsuario=u["idUsuario"], nombre=nombre.valor(),
                            usuarioAcceso=acceso.valor(), contrasena=contrasena.valor(), idSucursal=sucursal.valor())
            if r:
                d.resultado = r
                d.destroy()

        d.botones("Guardar cambios", guardar)
        nuevo = d.mostrar()
        if nuevo:
            self._actualizar_sesion_propia(nuevo)
            self.cargar()

    def asignar_rol(self, u):
        d = Dialogo(self.app, "Asignar rol")
        w.etiqueta(d.cuerpo, f"{u['nombre']} · {u['usuarioAcceso']}", "tenue", bg=t.BLANCO).pack(anchor="w", pady=(0, 14))
        opciones = w.Opciones(d.cuerpo, [(ROL_EMPLEADO, "Empleado"), (ROL_ADMINISTRADOR, "Administrador")])
        opciones.pack(fill="x", pady=(0, 16))
        opciones.fijar(u["rol"])

        def guardar():
            r = self.llamar("usuarios.asignar_rol", idUsuario=u["idUsuario"], rol=opciones.valor())
            if r:
                d.resultado = r
                d.destroy()

        d.botones("Guardar rol", guardar)
        nuevo = d.mostrar()
        if nuevo:
            if self._actualizar_sesion_propia(nuevo):
                return
            self.cargar()

    def _actualizar_sesion_propia(self, nuevo) -> bool:
        """Si el administrador se modificó a sí mismo, refleja el cambio; si cambió su
        rol, sus permisos cambian en consecuencia (postcondición del CU-12)."""
        if nuevo["idUsuario"] != self.app.usuario["idUsuario"]:
            return False
        cambio_rol = nuevo["rol"] != self.app.usuario["rol"]
        self.app.usuario = nuevo
        if cambio_rol:
            self.app.aviso("Tu rol cambió; se mostrará el menú de tu nuevo perfil.")
            self.app.mostrar("menu")
        return cambio_rol


def registrar(app):
    app.registrar_pantalla("login", InicioSesion)
    app.registrar_pantalla("usuarios", GestionUsuarios)
    app.registrar_tarjeta(TarjetaMenu("usuarios", "Gestionar usuarios", "Registrar / modificar / asignar rol", "usuario",
                                      (ROL_ADMINISTRADOR,), SOLO_ADMIN, {ROL_ADMINISTRADOR: 3}))
