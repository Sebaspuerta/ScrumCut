# Diseño aprobado

Única referencia visual de ScrumCut. Lo extraído aquí sale de las maquetas aprobadas por Sebastián:

- `docs/diseno/maquetas/Main.dc.html`: tablero (resumen ejecutivo).
- `docs/diseno/maquetas/Login.dc.html`: inicio de sesión.

Las maquetas son de una herramienta de diseño, no código de producción: no se sirven ni se copia su JS. Sus datos (nombre de la barbería, personas, cifras) son de ejemplo; la identidad de cada barbería es dato de `tenancy.Barbershop` (regla 2).

Lo que no esté aquí no está aprobado: se pregunta antes de construirlo.

## Paleta

| Uso | Color |
|---|---|
| Café espresso (barra superior, cifras, botones principales) | `#2E211A` |
| Tonos de café | `#3A2B22` · `#4A382D` · `#6B5444` · `#A68B76` · `#CBB8A6` · `#E4DAD0` |
| Acento: verde salvia | `#5E7361` |
| Acento sobre café | `#9DB09F` |
| Fondo piedra | `#EEEBE6` |
| Superficie del menú lateral | `#F3F0EB` |
| Líneas | `#D9D2C8` |
| Texto | `#1E1915` |
| Texto secundario | `#6E655D` |
| Fondo del login | degradado de `#6B5444` a `#EFE6DA` |

Tonos de apoyo que usan las maquetas:

| Uso | Color |
|---|---|
| Texto sobre café | `#F2EDE7` |
| Texto secundario sobre café | `#BFAE9F` |
| Texto del menú lateral | `#4A4039` |
| Título de grupo del menú ("Operación") e ítems sin pantalla todavía | `#6B5444` (`--color-espresso-600`, contraste AA 6,2:1 sobre el menú) |
| Celda de la marca en la barra superior | `#241912` |
| Línea inferior de la barra superior | `#1B130E` |
| Paneles y menús | `#FBFAF8`, con líneas `#E4DCD2` |
| Contador de alertas | el acento `#5E7361` con texto blanco (contraste AA 5,1:1) |
| Borde de controles (selects, botones secundarios) | `#CFC6BA` |
| Panel flotante (asistente) | `#F8F6F3` |
| Texto claro del login (foto, botón) | `#F7F1E9` |
| Línea del login | `#C4AE99` |
| Paradas intermedias del degradado del login | `#8E7461` 30 % · `#B89F89` 52 % · `#D8C7B5` 72 % (ángulo 100°) |

**Sin rojos.** Lo negativo se marca con signo y flecha, no con color: `▴ +12,4 %`, `▾ −3,1 %`, `▾ −$8.000 · faltante`. Lo positivo usa el acento (`#9DB09F` sobre café, `#5E7361` sobre claro); lo negativo, `#E4DAD0` sobre café y `#6B5444` sobre claro.

## Tipografía

- **Bricolage Grotesque** (500, 600, 700): títulos y cifras grandes. Es la versión variable (pesos y tamaño óptico): el trazo se ajusta solo al tamaño del texto.
- **Hanken Grotesk** (400, 500, 600): texto.
- Cifras tabulares (`font-variant-numeric: tabular-nums lining-nums`) en toda cifra.

| Elemento | Tamaño |
|---|---|
| h1 | 40px, Bricolage 600, interletrado −0,02em |
| h2 | 20px, Bricolage 600 |
| Texto | 14px, Hanken 400, interlineado 1,5 |
| Etiquetas | 11px, mayúsculas, interletrado 0,14em (0,18em en títulos de grupo) |

Otros tamaños de las maquetas: cifras de los indicadores 30px (Bricolage 500), título del login 34px, texto pequeño 12–13px.

## Íconos

Lucide, trazo 1.5, en línea (SVG dentro del HTML) con `currentColor`. Los archivos están en `frontend/templates/icons/` tal como los publica `lucide-static` v1.52.0, con trazo 2; el trazo 1.5 se aplica al usarlos.

Íconos del diseño: `layout-dashboard`, `calendar`, `receipt`, `banknote`, `users`, `notebook-pen`, `star`, `tag`, `package`, `chart-column`, `git-compare-arrows`, `bell`, `panel-left`, `map-pin`, `chevron-down`, `check`, `message-circle`, `user-cog`, `shield-check`, `history`, `settings`, `download`, `log-out`.

## Estructura

**Barra superior café** (`#2E211A`), de 64px:

- Celda de la marca (`#241912`), del mismo ancho que la barra lateral para formar una L: botón que abre y cierra la barra lateral (`panel-left`), monograma (iniciales en un cuadro con borde `#6B5444`), nombre de la barbería y "Barbería" en versalitas.
- Selector de sede (`map-pin`, rótulo "Sede" y la sede actual). Despliega "Todas las sedes · vista consolidada" (solo con `sedes.ver`), las sedes permitidas con una marca (`check`) en la actual y "Gestionar sedes" (solo con `sedes.gestionar`). Cambia de sede con un POST.
- Alertas (`bell`) con su contador sobre el acento, por alcance de sede.
- Administración (`settings`, texto y `chevron-down`): un panel ancho bajo la barra, del borde de la barra lateral a la derecha, con seis grupos en rejilla: Barbería, Equipo, Catálogo y precios, Clientes y fiados, Seguridad y datos, Cuenta y plan. Cada ítem aparece solo con su permiso; lo que aún no tiene pantalla va apagado con la etiqueta "Próximamente" y nunca es enlace. A la derecha, un resumen sobre café: sedes activas frente al límite del plan con su barra, usuarios activos y el último cambio de la auditoría. Si el rol no ve ningún ítem, el botón no aparece.
- Cuenta (iniciales en círculo, nombre y rol): cabecera con nombre, rol, barbería y sede; verificación en dos pasos; "Cerrar sesión en todos los dispositivos" y "Cerrar sesión" (`log-out`, en el color de texto normal), ambos por POST.
- "+ Nuevo" (`plus`, claro sobre la barra: fondo `#F2EDE7`, texto `#2E211A`) con las acciones que ya tienen pantalla y que el rol puede usar: nueva comanda, cobro rápido y registrar gasto.
- El buscador global y la Ayuda de la maqueta esperan a que exista su backend.
- Exportar no va en la barra: va en el encabezado de cada página que exporta.

**Barra lateral de trabajo diario**, contraíble (248px abierta, 72px cerrada; solo íconos al cerrarse, con `title` y `aria-label`), sobre `#F3F0EB` con línea a la derecha. Grupos en versalitas que se ocultan al cerrarla:

- Operación: Tablero (`layout-dashboard`), Agenda (`calendar`), Comandas (`receipt`), Caja (`banknote`).
- Clientes: Clientes (`users`), Fiados (`notebook-pen`), Reseñas (`star`).
- Catálogo: Servicios (`tag`), Inventario (`package`).
- Análisis: Reportes (`chart-column`), Comparativo de sedes (`git-compare-arrows`).
- Lo que aún no tiene pantalla va en `#6B5444` con la etiqueta "Pronto" y sin enlace. Alertas no está aquí: está en la campana.
- Elemento activo: fondo `#E4DAD0`, texto café en 600 y una marca de 3px en el acento a la izquierda.
- Al pie: botón Asistente (`message-circle`) y la firma "ScrumCut · por ScrumTech Solutions".
- En el celular es un panel que se abre desde la marca, cerrado al entrar; sin JavaScript queda arriba del contenido. Nunca hay scroll horizontal.

**Menús**: son `<details>` nativos y abren sin JavaScript. Un JavaScript propio, sin frameworks, deja uno solo abierto, los cierra con Esc o con un clic fuera, mantiene `aria-expanded` y devuelve el foco al botón. Nada se guarda en el navegador: la barra lateral abre por defecto en escritorio y cerrada en el celular.

**Contenido:** máximo 1600px de ancho (centrado por encima de ese ancho), 40px de margen, 56px entre secciones. Cada sección empieza con una línea café de 1px y su h2 con una descripción corta en texto secundario. Pie con "ScrumCut · por ScrumTech Solutions" y los enlaces a Términos, Privacidad y Cookies.

**Tablero "Resumen ejecutivo":** ruta "Inicio / Tablero", h1, "Sede … · actualizado …", el selector de mes (`?mes=AAAA-MM`) y "Exportar a Excel" (`download`). Debajo, la franja de indicadores, las ventas por día, el cuadre de caja de hoy (en "todas" pide elegir una sede), el rendimiento por barbero con la mezcla de ingresos, las alertas sin leer, los productos más vendidos y los últimos cierres.

Todo control mide al menos 44px de alto.

**Comandas** (`Comandas.dc.html`): ruta, h1 y "Sede … · fecha · precios de la sede …", con "Cobro rápido" (borde café) y "Nueva comanda" (café). A la izquierda, la lista: pestañas Abiertas, Cerradas hoy y Anuladas con su conteo (enlaces con `aria-current`), búsqueda por cliente o número y filtro por barbero; cada fila con cliente, total, número, barberos, tiempo o forma de pago e ítems, y la elegida sobre `#E4DAD0` con la marca en el acento. A la derecha, la comanda: cliente con su historial en la sede y el celular enmascarado, las líneas (ítem, barbero, cantidad, precio, total y quitar), "Agregar servicio o producto" con su barbero, subtotal, descuento y total, y el cobro: una casilla por cada forma de pago habilitada (Efectivo, Nequi, Daviplata, Tarjeta, Transferencia, Bre-B) y Fiado; Efectivo con "Recibido" y vueltas, las demás con referencia opcional, y Fiado con lo que debe en la sede y su cupo (solo con cliente registrado). "Dividir el pago" (con JavaScript) agrega hasta 3 filas de forma y monto, que deben sumar exactamente el total; las vueltas son solo sobre la parte en efectivo. "Cambiar cliente" busca por nombre o celular y permite dejarla como cliente de mostrador. "Anular comanda" pide motivo y confirmación.

**Caja** (`Caja.dc.html`): siempre de una sede. Estado "Abierta" con quién y desde cuándo ("desde las 8:00 a. m.", "desde ayer, 8:00 a. m." o "desde el lun 19 oct, 8:00 a. m."). Una caja que viene de otro día muestra el aviso "Esta caja viene de otro día. Ciérrala con su arqueo y abre la de hoy.", no recibe efectivo y su única acción es el arqueo; el tablero y Comandas muestran un aviso corto con enlace a Caja. botones "Registrar gasto", "Registrar retiro" y "Hacer arqueo y cerrar". Franja café con base, ventas en efectivo, abonos, gastos, retiros y esperado. Movimientos de hoy (hora, tipo, concepto, quién y monto con signo, sin rojos) con filtro por tipo y, debajo, "Otros medios" que no entran a la caja física. Arqueo por denominación (billetes de $100.000 a $1.000 y monedas en total), esperado, contado y diferencia con signo y flecha; con diferencia, la nota es obligatoria. Al final, los últimos 5 cierres de la sede.

**Clientes** (`Clientes.dc.html`): ruta, h1 y "Sede … · nivel e historial de cada cliente en esta sede", con "Nuevo cliente". Cuatro cifras en una fila abierta con líneas (activos en 90 días, nuevos este mes frente al anterior, vuelven en 30 días y con fiado). La lista: búsqueda por nombre, celular o cédula, orden y filtros por nivel como botones con `aria-pressed` y su conteo; columnas cliente (con el celular enmascarado), nivel, visitas, última visita, gasto de 90 días y deuda. La ficha: iniciales, nombre, celular enmascarado y "cliente desde"; nivel en la sede con su barra al siguiente; ticket, gasto, barbero habitual y lo que más pide; la deuda con su enlace al fiado; preferencias; últimas 5 visitas y "Nueva comanda para …". Los niveles son los del backend: Nuevo, Frecuente, VIP, Inactivo y Deudor; en "todas" la columna dice "Varía por sede".

**Fiados** (`Fiados.dc.html`): ruta, h1 y "Sede … · lo que deben los clientes en esta sede y sus abonos", con "Registrar abono". Franja café con por cobrar, vencido, vence en 7 días y cobrado en el mes. Antigüedad de la deuda en una barra apilada (al día, 1 a 15, 16 a 30 y más de 30 días), más oscura cuanto más vieja, con su leyenda. Pestañas Pendientes, Vencidos y Pagados en el mes; la lista por urgencia con el estado en texto ("▾ Vencido hace N días", "Vence en N días", "Al día"). El panel de abono: total, abonado y saldo, monto con "Pagar todo", formas de pago con la nota de si entran a la caja física, nota opcional y los abonos anteriores. En "todas" se ve la cartera, pero para abonar se elige la sede del fiado.

## Espacios

- Escala única para margin, padding y gap: 4, 8, 12, 16, 24, 32, 40, 56 y 72px (`--space-*` en `tokens.css`). Ningún espacio fuera de ella; lo revisa `tests/frontend/test_spacing_scale.py`.
- Contenido: 40px de margen en escritorio y 16px en el celular, todo alineado al mismo borde izquierdo.
- Secciones: 56px entre ellas. Una sección abierta (sin caja) empieza con una línea café de 1px y 16px de aire arriba, con 16px entre el título y el contenido.
- Tablas: filas de 44px, cifras a la derecha con `tabular-nums` y encabezados de 11px en mayúsculas.
- Componentes compartidos (`frontend/static/css/components/`): secciones, tablas, pestañas, franja oscura, totales, fila de cifras, filtros con `aria-pressed` (chips) e historial corto.

## Reglas

- Radio único de 4px (2px en las barras de las gráficas).
- Líneas de 1px.
- Sin tarjetas anidadas.
- Sin sombras, salvo menús flotantes (`0 12px 32px rgba(46, 33, 26, 0.16)`).
- Sin degradados, salvo el fondo del login y el desvanecido de su foto.
- Los bloques de indicadores van sobre café, separados por líneas de `#4A382D`.

## Gráficas aprobadas

- **Tabla calendario de ventas por día** (vista por defecto, `?vista=tabla`). Columnas de lunes a domingo y "Semana" con el total de cada semana; cada casilla, el número del día y lo vendido. Cinco tonos según lo vendido frente al mejor día del mes (`#F6F3EF`, `#EDE6DD`, `#E2D6C8`, `#D4C2B0`, `#C4AD97`). Días futuros vacíos con borde punteado; hoy, con un aro de 2px en el acento; un día pasado sin ventas dice "Sin ventas". Leyenda "Menos ■■■■■ más ventas · Valores en pesos colombianos (COP)". Al lado, total del mes, mejor día, promedio diario (solo días con ventas) y último día con ventas; debajo, el promedio por día de la semana. Los botones "Tabla | 3D" son enlaces con `aria-current`: la vista va en la URL, nunca en el navegador.
- **Torres 3D de ventas por día** (`?vista=3d`, mejora progresiva: sin JavaScript se ve la tabla). Una cuadrícula de 7 columnas (lunes a domingo) por semanas; cada torre es un día y su altura, lo vendido. La cara superior toma cinco tonos de café según el nivel (`#E4DAD0`, `#CBB8A6`, `#A68B76`, `#6B5444`, `#2E211A`); hoy y la torre bajo el cursor, el acento. Gira con el cursor (inclinación limitada) y con botones ↺ ↻ y "Vista inicial". El número del día va en el piso; los días futuros, con borde punteado. Un recuadro café con el día y su valor sigue al cursor.
- **Cascada del cuadre de caja.** De la apertura al dinero esperado: apertura y esperado en café, ventas en efectivo y abonos en el acento, gastos y retiros en `#CBB8A6`, y el contado con borde café de 1,5px sin relleno. Debajo, la diferencia del arqueo sobre `#E4DAD0`, con signo y flecha.
- **Barras por barbero con comisión.** Barra café de 10px sobre una pista `#E4DAD0`, proporcional a las ventas del primero; a la derecha, ventas y comisión (en el acento).
- **Barra de mezcla de ingresos.** Una barra de 12px dividida en servicios (café) y productos (acento), con porcentaje y monto de cada parte.

## Inicio de sesión

- Foto en tonos café (escala de grises con sepia) a la izquierda, que se desvanece hacia el fondo; sobre ella, la etiqueta "Gestión ejecutiva para barberías" y la frase "Cada corte, cada venta y cada cierre de caja, en un solo lugar."
- Formulario sobre crema: título "Iniciar sesión", correo, contraseña con "¿Olvidaste tu contraseña?", botón café "Entrar", la nota sobre el código de verificación en dos pasos para dueños y administradores, y "Crear cuenta".
- Al pie, el logo de ScrumCut en 3D, pequeño, que gira con el cursor; por ahora es el nombre en texto con capas de café (de `#2E211A` a `#C4AE99`). El logo definitivo lo entrega Sebastián. Debajo, "por ScrumTech Solutions" y los enlaces a Términos, Privacidad y Cookies.

## Asistente

Va en la interfaz pero **sin funcionalidad**: el panel flotante muestra "El asistente estará disponible pronto" y el campo de pregunta deshabilitado. Su lógica se implementa al final del proyecto, cuando el backend esté completo.

## Recursos

- Fuentes: `frontend/static/fonts/`, woff2 latin de Fontsource 5.3.0, con sus licencias OFL: Bricolage Grotesque variable (`@fontsource-variable/bricolage-grotesque`, ejes `wght` 200–800 y `opsz` 12–96) y Hanken Grotesk estática (`@fontsource/hanken-grotesk`, 400, 500 y 600).
- Variables: `frontend/static/css/tokens.css`.
- Íconos: `frontend/templates/icons/`, de `lucide-static` v1.52.0, con su licencia ISC.
- Foto del login: `frontend/static/img/login-barbero.webp`. Foto: Tim Collins Photography — uso autorizado; conservar el crédito.

## Pendientes de diseño

Cada uno requiere aprobación antes de construirse:

- Modo oscuro.
- Versión móvil de las pantallas (el marco ya tiene la suya: la barra lateral como panel).
- Las pantallas de cada módulo.
