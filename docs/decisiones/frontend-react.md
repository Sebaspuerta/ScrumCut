# Decisión: frontend interno en React + TypeScript

Fecha: 2026-10-22 · Estado: aceptada (fase R0)

## Contexto

La interfaz se construyó con plantillas de Django, HTMX y JavaScript propio sin frameworks (fases F1 a F4). Las pantallas que vienen (agenda con arrastre, comandas en vivo, caja con varias personas a la vez) son muy dinámicas: con plantillas y JavaScript suelto, el estado de pantalla queda repartido entre el servidor y scripts pequeños, sin tipos y difícil de probar.

## Decisión

- La parte interna de la app (lo que se usa después de iniciar sesión) pasa a **React + TypeScript**, servida en `/app/`.
- **Inicio de sesión, registro, recuperación de contraseña y 2FA siguen en Django** (allauth y axes), con sus límites de intentos.
- El backend expone una API en `/api/v1/` con Django REST Framework; el esquema OpenAPI lo genera drf-spectacular.

## Razones

- Interfaz dinámica: agenda, comandas en vivo y caja necesitan estado en pantalla que se actualice sin recargar.
- Organización por componentes: cada parte de la pantalla es un archivo pequeño, con su CSS y sus pruebas.
- Tipado: los tipos salen del esquema de la API, así que un cambio en el backend rompe la compilación y no la pantalla en producción.
- Demanda laboral: React y TypeScript son lo más pedido; facilita sumar personas al proyecto.

## Costos

- Dos cadenas de herramientas (Python y Node) en desarrollo, en pre-commit y en CI.
- Más dependencias de terceros que vigilar (`npm audit` en CI).
- Durante la migración conviven dos interfaces: plantillas y React.
- Un paso de compilación (`vite build`) antes de `collectstatic` en el despliegue.

## Reglas que no se negocian

1. Toda regla de negocio, permiso y alcance de sede vive en el backend; el frontend solo muestra lo que la API le da.
2. La sesión sigue en la cookie HttpOnly del mismo dominio: nada de tokens, ni JWT, ni datos en localStorage o sessionStorage.
3. CSRF en toda escritura: DRF con `SessionAuthentication` únicamente. La cookie CSRF es HttpOnly, así que la app pide el token a `/api/v1/csrf/` y lo guarda solo en memoria.
4. La CSP estricta se mantiene en producción: Django entrega el HTML de `/app/` sin scripts en línea, leyendo el manifest de Vite.
5. Migración por módulos: las pantallas en plantillas siguen funcionando hasta que su versión en React las reemplace.
6. Los tipos de TypeScript se generan del esquema OpenAPI (`npm run gen:types`), nunca se escriben a mano. Una prueba de pytest falla si el esquema no coincide con la API, y una de Vitest si los tipos no coinciden con el esquema.

## Cómo se sirve

- **Producción:** `vite build` deja los archivos en `frontend/static/app/` (con `manifest.json`); Django los sirve como estáticos. La vista `react_app` (con `login_required`) entrega `/app/` y sus subrutas con la plantilla `app/index.html`. La CSP no cambia.
- **Desarrollo:** el servidor de Vite (5173) atiende `/app/` y pasa todo lo demás (API, cuenta, estáticos y pantallas en plantillas) a Django (8000), conservando el Host para que la comprobación CSRF vea el mismo origen. La CSP no se relaja: la página de Vite no la sirve Django y las de Django conservan la suya.
