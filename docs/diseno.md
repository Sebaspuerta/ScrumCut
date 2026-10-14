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

Íconos del diseño: `layout-dashboard`, `receipt`, `banknote`, `users`, `tag`, `package`, `notebook-pen`, `chart-column`, `bell`, `panel-left`, `message-circle`, `user-cog`, `shield-check`, `history`, `settings`, `download`.

## Estructura

**Barra superior café** (`#2E211A`):

- A la izquierda: botón que contrae el menú lateral (`panel-left`), iniciales y nombre de la barbería con la etiqueta "Barbería".
- Administración: Gestión de barberos (`user-cog`), Usuarios y roles (`shield-check`), Auditoría (`history`), Ajustes (`settings`).
- Separador de 1px, botón Exportar (`download`, con borde), Alertas (`bell`, con contador en el acento) y la cuenta (iniciales en círculo, nombre y rol).

**Menú lateral de operación**, contraíble (236px abierto, 72px cerrado; solo íconos al cerrarse), sobre `#F3F0EB` con línea a la derecha:

- Grupo "Operación": Tablero (`layout-dashboard`), Comandas (`receipt`), Caja (`banknote`), Clientes (`users`), Servicios (`tag`), Inventario (`package`), Fiados (`notebook-pen`), Reportes (`chart-column`), Alertas (`bell`, con contador).
- Elemento activo: fondo `#E4DAD0`, texto café en 600 y una marca de 3px en el acento a la izquierda.
- Al pie: botón Asistente (`message-circle`) y la firma "ScrumCut · por ScrumTech Solutions".

**Contenido:** máximo 1600px de ancho (centrado por encima de ese ancho), 40px de margen, 56px entre secciones. Cada sección empieza con una línea café de 1px y su h2 con una descripción corta en texto secundario. Pie con enlaces a Términos, Privacidad y Cookies.

Todo control mide al menos 44px de alto.

## Reglas

- Radio único de 4px (2px en las barras de las gráficas).
- Líneas de 1px.
- Sin tarjetas anidadas.
- Sin sombras, salvo menús flotantes (`0 12px 32px rgba(46, 33, 26, 0.16)`).
- Sin degradados, salvo el fondo del login y el desvanecido de su foto.
- Los bloques de indicadores van sobre café, separados por líneas de `#4A382D`.

## Gráficas aprobadas

- **Torres 3D de ventas por día.** Una cuadrícula de 7 columnas (lunes a domingo) por semanas; cada torre es un día y su altura, lo vendido. La cara superior toma cinco tonos de café según el nivel (`#E4DAD0`, `#CBB8A6`, `#A68B76`, `#6B5444`, `#2E211A`); hoy y la torre bajo el cursor, el acento. Gira con el cursor (inclinación limitada) y con botones ↺ ↻ y "Vista inicial". Los días cerrados se marcan con borde punteado en el piso. Al lado, una lectura del día señalado y los totales del período; debajo, el promedio por día de la semana.
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
- Versión móvil.
- Las pantallas de cada módulo.
