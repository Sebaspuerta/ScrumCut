# Arquitectura

Documento fuente (vivo): [ScrumCut v2 — Arquitectura y migración desde MAGNUS v1](https://claude.ai/code/artifact/d09db44f-1673-41f6-83a3-5e4b4bde921a).

## Resumen de decisiones

- Monolito modular en Django; reglas en `services.py`, lecturas en `selectors.py`.
- Multi-barbería en dos barreras: managers filtrados (`TenantScopedModel`) + Row-Level Security en PostgreSQL (`EnableTenantRLS`).
- El rol vive en `Membership` (persona × barbería). Roles: Dueño, Administrador, Cajero, Barbero, Consultor.
- Sesión en cookie `HttpOnly`/`Secure`; sin tokens en el navegador.
- Correo verificado obligatorio; 2FA obligatorio para Dueño, Administrador y equipo de plataforma.
- Bloqueo por usuario + IP (axes) y límites de allauth en login, registro y recuperación.
- La app no arranca si falta un secreto.

## Fases

0. Fundaciones (este repositorio hoy)
1. Operación diaria: catálogo, personal, clientes, comandas, caja, inventario, fiados
2. Gerencia: reportes, alertas programadas
3. Agenda y reservas públicas
4. Producción: dominio, despliegue, pentest
v3. Pagos en línea
