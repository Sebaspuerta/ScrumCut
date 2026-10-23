# Arquitectura

## Resumen de decisiones

- Monolito modular en Django; reglas en `services.py`, lecturas en `selectors.py`.
- Multi-barbería en dos barreras: managers filtrados (`TenantScopedModel`) + Row-Level Security en PostgreSQL (`EnableTenantRLS`).
- El rol vive en `Membership` (persona × barbería). Roles: Dueño, Administrador, Cajero, Barbero, Consultor.
- Sesión en cookie `HttpOnly`/`Secure`; sin tokens en el navegador.
- Correo verificado obligatorio; 2FA obligatorio para Dueño, Administrador y equipo de plataforma.
- Bloqueo por usuario + IP (axes) y límites de allauth en login, registro y recuperación.
- La app no arranca si falta un secreto.
- La parte interna migra a React + TypeScript en `/app/` sobre una API DRF en `/api/v1/` (solo sesión y CSRF); login, registro, recuperación y 2FA siguen en Django. Ver [decisiones/frontend-react.md](decisiones/frontend-react.md) y "Frontend en React".

## Hallazgos de seguridad de MAGNUS v1

Patrones que no se repiten al portar (regla 1 de `AGENTS.md`). Detalle y defectos funcionales en [migracion-magnus.md](migracion-magnus.md).

| # | Hallazgo | Origen en MAGNUS | En ScrumCut |
|---|---|---|---|
| S1 | `SECRET_KEY` con valor por defecto en el código: cualquiera puede firmar tokens válidos | `config.py` | `config.env.require`, sin valores por defecto |
| S2 | JWT en `localStorage`, 8 h de vida, sin revocación; cambiar la contraseña no invalida tokens | `utils/security.py`, frontend | Sesión en cookie `HttpOnly`/`Secure`; rotación al iniciar sesión |
| S3 | Código maestro global que restablece la contraseña de cualquier usuario, incluido el administrador; su bloqueo también es global | `services/master_code_service.py` | Recuperación por correo verificado (allauth) |
| S4 | Bloqueo de inicio de sesión solo por usuario (cualquiera bloquea cuentas ajenas) y mensaje distinto para usuario inactivo (revela que existe) | `security_service.authenticate_user` | axes por usuario + IP; mensaje único |
| S5 | Autoridad de dueño decidida por nombre de usuario fijo (`mateo`, `admin`) | `utils/security.require_owner`, `barber_service.is_owner_barber`, `security_service.deactivate_user` | Rol Dueño en `Membership` |
| S6 | `str(e)` devuelto al usuario | `order_service.close_order` | Mensaje genérico; detalle solo en logs |
| S7 | Política de contraseñas inconsistente (6 caracteres al cambiarla, 8 en otros flujos) y sin lista de contraseñas comunes | `security_service.change_password` | Validadores de Django en todos los flujos |
| S8 | Administrador inicial con usuario predecible (`admin`) y contraseña desde `.env` | `security_service.seed_initial_security` | Alta de barbería con dueño y correo verificado |
| S9 | Sin filtro por dueño del objeto: un barbero lista y abre todas las comandas por id | `order_service.list_orders`, `get_order_by_id` | Selectores filtran por barbero (regla 5) |
| S10 | Precio enviado por el cliente: el ítem de producto toma `unit_price` del payload y cualquier ítem se puede editar de precio | `order_service.add_order_item`, `update_order_item` | Precio siempre del catálogo; cambio de precio con permiso propio y auditoría |
| S11 | Escrituras protegidas con un permiso de lectura (`alertas.ver` crea y marca alertas) | `routes/alerts_routes.py` | Una acción por permiso en `roles.py` |
| S12 | `python-jose` para JWT, librería poco mantenida con avisos de seguridad publicados | `backend/requirements.txt` | No se usan JWT |

## Fases

0. Fundaciones — completa.
1. Operación diaria: catálogo, personal, clientes, comandas, caja, inventario, fiados — lógica de dominio completa (pasos 1 a 7 de la migración de MAGNUS); falta la interfaz y los pendientes de seguridad de la fase 1.
2. Gerencia: reportes, alertas programadas — lógica de dominio completa (pasos 8 y 9 de la migración de MAGNUS); falta la interfaz.
3. Agenda y reservas públicas — sin empezar.
4. Producción: dominio, despliegue, pentest — sin empezar.
v3. Pagos en línea — sin empezar.

### Multi-sede

Especificación, diagnóstico y conflictos por decidir en [sedes.md](sedes.md). La barbería sigue siendo la frontera de seguridad (RLS); la sede se controla en servicios, selectores y permisos.

- S1. Modelo de datos — hecho.
- S2. Alcance por petición, solo backend — hecho.
- S3. Ajustes → Sedes, selector de sede y modo "todas" — el selector de sede de la barra superior y la vista consolidada están hechos (frontend F1); falta la pantalla de Ajustes → Sedes.
- S4a. Caja, comandas, gastos y precios por sede — hecho (backend).
- S4b. Inventario por sede y traslados — hecho (backend).
- S5. Consolidado y comparativo — hecho (backend: comparativo y Excel por sede); falta su pantalla.

## Frontend en React

Decisión, razones, costos y reglas en [decisiones/frontend-react.md](decisiones/frontend-react.md). El estándar de código está en `AGENTS.md`.

| Pieza | Dónde |
|---|---|
| API (DRF + drf-spectacular) | `backend/apps/api`: `me`, `navigation`, `branch` (cambio de sede con `choose_branch`) y `csrf`, en `/api/v1/`. Solo `SessionAuthentication`, permiso `HasRolePermission` sobre `role_has_permission`, alcance de `request.branch_scope`, errores genéricos (`apps/api/exceptions.py`), paginación de 50 y límites de 30/min sin sesión y 300/min con sesión. Sin API navegable ni esquema publicado. |
| Esquema y tipos | `frontend/app/openapi.json` (de `manage.py spectacular`) y `frontend/app/src/api/schema.d.ts` (de `npm run gen:types`). `tests/api/test_openapi_schema.py` y `src/api/schema.test.ts` fallan si alguno quedó desactualizado. |
| App | `frontend/app/`: Vite, React Router (base `/app`), TanStack Query. Compila en `frontend/static/app/`. |
| Página | `apps.core.views.react_app` (`login_required`) en `/app/` y subrutas; lee el manifest de Vite con `apps/core/vite_manifest.py` y pinta `frontend/templates/app/index.html`, sin nada en línea. |
| Tokens | `frontend/app/src/styles/tokens.css`, provisionales hasta R1. |

| Tablero y marco (R1) | `apps/api`: `dashboard` (sobre `executive_dashboard`, `reportes.ver`, consultas constantes), `notifications` (alertas, solo lectura, `alertas.ver`) y `me/preferences` (tema, PATCH con CSRF). `User.theme` (migración `accounts` 0003). En React: marco, paleta de comandos, notificaciones, Administración, tema y tablero en `/app/`. |

Fases: R0 (base técnica) — hecha. R1 (identidad nueva, marco y tablero en React; entrada de Django con la identidad nueva) — hecha. Identidad: [diseno/identidad-r1.md](diseno/identidad-r1.md).

## Pendientes de seguridad

| Pendiente | Fase | Estado |
|---|---|---|
| Botón "cerrar sesión en todos los dispositivos", con prueba | 1 | Hecho (lógica y prueba; el botón visual llega con la interfaz) |
| Honeypot en registro y recuperación de contraseña | 1 | Hecho |
| Prueba de que el logout invalida la sesión en el servidor | 1 | Hecho |
| Textos legales redactados, aprobados y publicados; aceptación al registrarse | 1 | Lógica hecha (aceptación, registro cerrado sin documentos, chequeo de despliegue); textos pendientes de Sebastián |
| Meta títulos y descripciones, datos estructurados (schema.org), sitemap y robots.txt en páginas públicas | Frontend | Pendiente |
| Favicon completo (.ico, apple-touch-icon, 192 y 512 px) con el logo definitivo | Frontend | Pendiente |
| Desactivar la caché de historial de htmx (sessionStorage) al montar el frontend | Frontend | Pendiente |
| Honeypot en reservas públicas | 3 | Pendiente |
| Usuario de base de datos de la app sin BYPASSRLS ni dueño de las tablas, con prueba | 4 | Pendiente |
| HSTS de 1 día a 1 año | 4 | Pendiente |
| Correr la suite completa con un rol sin privilegios, igual al de producción | 4 | Pendiente |
| Rol de base de datos para migraciones en producción (las migraciones de datos recorren cada barbería con each_barbershop) | 4 | Pendiente |
| Ficha de Google Business de ScrumTech | Fuera del código | Pendiente |
