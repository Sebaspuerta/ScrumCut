# Identidad R1

Referencia aprobada: `docs/diseno/figma-make/src` (`App.tsx` e `index.css`). Es la única identidad vigente: se aplica a la app de React (`frontend/app`) y a la entrada de Django (login, registro, recuperación y 2FA), lo único que sigue en plantillas. La identidad anterior y sus maquetas quedan como historia en [historico/](historico/diseno.md).

Lo que no esté aquí no está aprobado: se pregunta antes de construirlo.

## Color

| Token | Claro | Oscuro |
|---|---|---|
| Fondo (`--color-bg`) | `#f5f3ee` | `#111311` |
| Superficie (`--color-surface`) | `#fcfbf8` | `#181b18` |
| Elevada (`--color-raised`) | `#fff` | `#20231f` |
| Barra lateral (`--color-side`) | `#edeae2` | `#0c0e0c` |
| Barra superior (`--color-top`) | `#fcfbf8` | `#181b18` |
| Línea (`--color-line`) | `#d7d3c8` | `#343832` |
| Texto (`--color-text`) | `#1b201c` | `#f2f0e9` |
| Texto secundario (`--color-muted`) | `#62685f` | `#a8afa4` |
| Acento (`--color-accent`) | `#876b32` | `#c7a85f` |
| Acento suave (`--color-soft`) | `#e8dfc8` | `#332c1d` |
| Positivo (`--color-positive`) | `#386248` | `#79a889` |
| Atención (`--color-attention`) | `#8a5b28` | `#d6a363` |
| Deshabilitado (`--color-disabled`) | `#a8aaa5` | `#666b64` |

**Sin rojos.** Lo negativo se marca con signo y flecha, no con color: `▴ +12,4 %`, `▾ −3,1 %`, `▾ −$8.000 · faltante`. Lo positivo usa el tono positivo o el acento.

## Tema

Por defecto sigue `prefers-color-scheme`. El botón de la barra superior lo cambia y la elección (`system`, `light` o `dark`) se guarda en el servidor (`User.theme`, `PATCH /api/v1/me/preferences/`). Django pone `data-theme` en `<html>` al entregar `/app/`, así que la página no parpadea. Nada se guarda en el navegador. La entrada sigue solo `prefers-color-scheme` (aún no hay sesión).

## Tipografía

- Libre Baskerville (400 y 700): la marca, los títulos y las cifras grandes.
- Manrope (400, 500, 600 y 700): la interfaz, con cifras tabulares.
- Alojadas: en la app por `@fontsource` (5.3.0); en la entrada, los mismos archivos en `frontend/static/fonts/` con su licencia OFL. Nada se pide a Google.

## Logo

`docs/diseno/marca/`: la navaja con doble aro (logo) y la compacta (favicon y celular), siempre con `currentColor`. Junto al símbolo, "SCRUMCUT" en Libre Baskerville 700 con interletrado 0,18em y "Gestión para barberías".

## Medidas

Barra superior de 72 px, barra lateral de 224 px (260 px como panel en el celular, bajo 900 px), contenido de hasta 1600 px. Todo control mide al menos 44 px (en la referencia algunos miden 36 o 40 px).

## Entrada (Django)

La referencia no trae la entrada; se le aplican los mismos tokens, fuentes y logo sin cambiar su estructura (foto a la izquierda, formulario a la derecha) ni sus clases propias (`entrance*`, `auth-*`, en `static/css/modules/login.css`; fuentes en `static/css/identity-fonts.css`). En el celular (bajo 900 px) la foto no se muestra. El logo 3D de texto y su `login-logo.js` se retiran: los reemplaza el logo SVG. Foto: `frontend/static/img/login-barbero.webp`, de Tim Collins Photography, con uso autorizado: su crédito se conserva.

Las páginas de error de Django (400, 403, 404, 500 y CSRF) usan el mismo layout sin la foto: logo, panel con el código, el título en Libre Baskerville, el mensaje y «Ir al inicio», y el pie (`static/css/modules/errors.css`, clases `error-page*`). Los colores de la identidad viven en `static/css/tokens.css` (`--identity-*`), claros y oscuros según el sistema. Los mensajes de error de la entrada tutean (`apps/accounts/adapter.py`).

## Formato

- Pesos colombianos sin decimales, con punto de miles y el signo menos tipográfico: `$1.250.000`, `−$8.000`. Sin dato, `—`.
- Fechas cortas `19 oct`, día `Lun 19 oct`, mes `Octubre 2026` y hora `8:00 a. m.`, en la zona horaria de la barbería.
- Una sola implementación por lado: `frontend/app/src/lib/format.ts` en React y `apps/core/formatting.py` en el backend (API, Excel y alertas). Los casos compartidos están en `frontend/app/src/lib/format-cases.json` y los prueban Vitest y pytest.

## Espacios

Escala única para margin, padding y gap: 4, 8, 12, 16, 24, 32, 40, 56 y 72 px (`--space-*`). Ningún espacio fuera de ella, ni en la app de React ni en la entrada; lo revisa `backend/tests/frontend/test_spacing_scale.py`. Solo se suman a la escala las medidas del marco fijo (alto de la barra superior, ancho de la lateral), y las excepciones van en esa prueba con su motivo.

## Forma

- Radio único de 4 px; líneas de 1 px.
- Sin tarjetas dentro de tarjetas.
- Sin sombras, salvo lo que flota: menús, la paleta de comandos y los avisos sobre una gráfica.
- Cifras tabulares (`tabular-nums lining-nums`) en toda cifra.

## Íconos

Lucide (`lucide-react` en la app), trazo 1,5, con `currentColor`. En la entrada, los SVG de `frontend/templates/icons/` (`lucide-static`, licencia ISC).

## Estados

Toda pantalla contempla sus estados vacío, cargando y error, y su aspecto también requiere aprobación. Los errores llevan un mensaje genérico (regla 12 de `AGENTS.md`).

## Gráficas del tablero

- Calendario de ventas por día (vista por defecto) y torres 3D (`?vista=3d`). La vista y el mes van en la URL, nunca en el navegador.
- Cada día con ventas toma uno de cinco tonos según lo vendido frente al mejor día del mes; los días futuros van con borde punteado.
