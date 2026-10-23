# Identidad R1

Referencia aprobada: `docs/diseno/figma-make/src` (`App.tsx` e `index.css`). Se aplica a la app de React (`frontend/app`) y a la entrada de Django (login, registro, recuperación y 2FA). Las pantallas internas que siguen en plantillas conservan la identidad anterior (`docs/diseno.md`) hasta que pasen a React.

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

Sin rojos: lo negativo va con signo y flecha (`▾ −3,1 %`). Radio de 4 px y la escala de espacios del proyecto (4, 8, 12, 16, 24, 32, 40, 56 y 72 px).

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

La referencia no trae la entrada; se le aplican los mismos tokens, fuentes y logo sin cambiar su estructura (foto a la izquierda, formulario a la derecha) ni sus clases propias (`entrance*`, `auth-*`, en `static/css/modules/login.css`; fuentes en `static/css/identity-fonts.css`). En el celular (bajo 900 px) la foto no se muestra. El logo 3D de texto y su `login-logo.js` se retiran: los reemplaza el logo SVG.
