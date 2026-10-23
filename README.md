# GameStar · Sistema de ventas, inventario y reparaciones

Punto de venta (POS) de escritorio en Python para la tienda/taller **GameStar**, construido a
partir del documento *PRY03 – Proyecto Semestral (Equipo Rosa)* y del prototipo
*GameStar Diseño Final*. Instituto Tecnológico Superior de Xalapa · Ingeniería de Software.

Solo usa la biblioteca estándar de Python (Tkinter, sqlite3, http.server): no requiere
pagos, suscripciones ni dependencias externas (restricción 1.4.3).

## Requisitos de instalación

- Python 3.10 o superior con Tkinter (el instalador oficial de Python para Windows y macOS
  ya lo incluye; en Linux, paquete `python3-tk`).
- Una computadora que actúe como servidor y al menos dos laptops, una por sucursal (1.4.2).

## Ejecución

| Dónde | Qué hacer |
|---|---|
| Computadora servidor | `python -m gamestar.servidor` (crea `datos/gamestar.db` y escucha en el puerto 8765) |
| Cada laptop de sucursal | En `config.ini`: `modo = red` y `servidor = <IP del servidor>`; luego `python -m gamestar` |
| Un solo equipo (pruebas/demostración) | `modo = local` en `config.ini`; luego `python -m gamestar` |

En el primer arranque no existen usuarios: la pantalla de inicio pide crear la cuenta del
administrador (dueño del local). Después, el administrador registra a los empleados en
**Gestionar usuarios**.

Pruebas automatizadas: `python -m unittest discover -s tests -t .`

## Ramas

| Rama | Contenido | Requisitos / casos de uso |
|---|---|---|
| `main` | Núcleo: esquema de base de datos (diagrama de clases 2.3), transacciones, control de acceso por rol, servidor central, conexión cliente y armazón de la interfaz | RNF02, RNF03, RNF06, RNF07, RFBD01, RFBD02, RFBD10 |
| `feature/usuarios-acceso` | Inicio de sesión, acceso denegado, gestionar usuarios | RF18–RF21, CU-01, CU-10, CU-11, CU-12 |
| `feature/reportes-bitacora` | Bitácora de auditoría inalterable, generar reportes, estadística de productos más vendidos | RF22–RF24, RFBD09, RNF04, CU-15 |
| `feature/inventario` | Consultar inventario, catálogo, alertas de stock bajo, movimientos | RF01–RF07, RFBD03, RFBD07, RFBD11, RFBD12, RNF01, CU-02, CU-07, CU-08, CU-09, CU-16 |
| `feature/ventas` | Registrar venta, registro de venta, historial de ventas | RF08–RF11, RFBD04–RFBD06, RNF02, RNF05, CU-03, CU-13 |
| `feature/reparaciones` | Flujo de 4 pasos (registrar, actualizar estado, refacciones usadas, entrega) y consultar reparaciones | RF12–RF17, RFBD08, RFBD10, CU-04, CU-05, CU-06, CU-14 |

Cada módulo vive en `gamestar/modulos/<módulo>/` con `servicios.py` (lógica de negocio) y
`pantallas.py` (interfaz). El núcleo los descubre automáticamente, así que integrar una rama
solo agrega su carpeta. Las ramas se integraron a `main` en este orden:
usuarios-acceso → reportes-bitacora → inventario → ventas → reparaciones.

## Estructura

```
gamestar/
  nucleo/        base de datos, esquema, reglas, seguridad, despachador de servicios
  cliente/       conexión de la interfaz (red o local)
  servidor.py    servidor central HTTP/JSON
  ui/            ventana, encabezado, menú por rol y componentes visuales
  modulos/       usuarios_acceso, reportes_bitacora, inventario, ventas, reparaciones
tests/           pruebas por rama
config.ini       modo de conexión y ubicación de la base de datos
```

## Cómo se atienden los requisitos no funcionales

- **RNF01 (< 2 s):** índices en la base de datos y búsqueda en el servidor; hay una prueba
  con 3 000 productos.
- **RNF02 (consistencia ante cortes):** cada operación es una transacción atómica; si la red
  se cae, la venta se completa o se revierte por entero. Cada venta lleva una clave única,
  por lo que reintentarla después de un corte no la duplica ni descuadra el stock.
- **RNF03 (acceso por rol):** el servidor valida el rol en cada llamada y el menú solo
  muestra las funciones del perfil. Un cambio de rol aplica de inmediato.
- **RNF04 (bitácora inalterable):** ventas, cambios de inventario y cambios de estado de
  reparaciones se registran con usuario, fecha y hora; disparadores de la base de datos
  impiden modificar o borrar la bitácora.
- **RNF05 (≤ 3 interacciones):** cantidad → «Agregar» → «Confirmar venta».
- **RNF06 (modularidad):** la lógica de negocio no depende de la interfaz; un lector de
  códigos de barras podría añadirse como otro módulo sin tocar el núcleo.
- **RNF07 (dos laptops simultáneas):** servidor multihilo con escrituras serializadas;
  hay una prueba con dos clientes vendiendo el mismo producto a la vez.

## Decisiones donde el documento no especifica un detalle

Estas decisiones son las mínimas necesarias para que el sistema funcione; se señalan para
que el equipo las valide o ajuste:

1. **Teléfono del cliente** en reparaciones: se agregó al modelo por el resultado 3 de la
   evaluación del prototipo y el diseño final; se pide como dato obligatorio.
2. **Importes** se guardan en centavos (SQLite no tiene tipo DECIMAL) y se muestran con formato 0.00.
3. **Cantidad inicial** de un producto nuevo (CU-07) se asigna a la sucursal del
   administrador que lo registra; en las demás sucursales inicia en 0.
4. **Entradas de mercancía:** el documento define "Entrada" (glosario, RFBD07) pero no un
   caso de uso propio; se registran desde el diálogo *Modificar producto* (sección opcional
   "Entrada de mercancía").
5. **Eliminar producto (RFBD11):** como todo producto tiene un registro de inventario por
   sucursal, se impide la eliminación si tiene existencias, ventas, refacciones usadas o
   movimientos; si no tiene nada de eso, se elimina junto con sus registros vacíos.
6. **Stock bajo:** existencia ≤ 5 o menor que el stock mínimo (glosario, CU-16 y nota del
   prototipo). El diccionario de datos dice "igual o menor" al mínimo; se siguió la mayoría
   de las fuentes.
7. **Siempre queda al menos un administrador:** no se permite quitar el rol al último.
8. **Registrar venta** es solo del empleado, como en el diagrama de casos de uso.
9. **Bitácora:** se registra pero no tiene pantalla, porque el diseño final no incluye una.
10. **RFBD13 (sincronización):** al haber una base de datos central, ambas sucursales ven el
    mismo inventario en tiempo real. Si la red falla, la operación no se aplica y se avisa
    al usuario; no hay un modo sin conexión con cola de pendientes.
11. **Registro de venta emitido:** se genera como comprobante digital de texto en la carpeta
    `comprobantes/` y se abre con el programa predeterminado.
12. **Datos base:** dos sucursales ("Sucursal 1" y "Sucursal 2") y las categorías
    Videojuegos, Consolas y Accesorios, tomadas de los ejemplos del documento.
13. **Historial de reparaciones:** las reparaciones nunca se borran, lo que cumple con
    conservarlas al menos una semana.

Fuera de alcance según 1.2.4: códigos QR y de barras, y cobro automático con tarjeta.
