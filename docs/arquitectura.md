# Arquitectura

## Resumen de decisiones

- Monolito modular en Django; reglas en `services.py`, lecturas en `selectors.py`.
- Multi-barbería en dos barreras: managers filtrados (`TenantScopedModel`) + Row-Level Security en PostgreSQL (`EnableTenantRLS`).
- El rol vive en `Membership` (persona × barbería). Roles: Dueño, Administrador, Cajero, Barbero, Consultor.
- Sesión en cookie `HttpOnly`/`Secure`; sin tokens en el navegador.
- Correo verificado obligatorio; 2FA obligatorio para Dueño, Administrador y equipo de plataforma.
- Bloqueo por usuario + IP (axes) y límites de allauth en login, registro y recuperación.
- La app no arranca si falta un secreto.

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
| Ficha de Google Business de ScrumTech | Fuera del código | Pendiente |
