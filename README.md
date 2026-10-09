# ScrumCut

Software de gestión para barberías, por [ScrumTech Solutions](https://www.instagram.com/scrumtech_solutions/).
Multi-barbería, 100 % web, con agenda, comandas, caja, inventario, fiados y reportes gerenciales.

Estado: **lógica de negocio de MAGNUS portada por completo** (pasos 1 a 9 de `docs/migracion-magnus.md`), sin interfaz todavía. Sobre las fundaciones de la fase 0: identidad segura, multi-barbería, auditoría y base legal.

## Stack

Django 6 · PostgreSQL (Row-Level Security por barbería) · django-allauth (correo verificado + 2FA) · django-axes · Argon2.

## Arranque local

```bash
python -m venv .venv && source .venv/bin/activate
cp .env.example .env        # completa los valores; ninguno tiene valor por defecto
pre-commit install
cd backend
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El `.env` vive en la raíz del repositorio; `manage.py` y las pruebas lo cargan desde ahí en desarrollo.

## Estructura

```
backend/
  config/          settings por ambiente (base, dev, test, prod) y lectura de entorno
  apps/core/       modelos base, contexto de barbería activa, operación RLS
  apps/accounts/   usuario por correo, 2FA obligatorio para roles privilegiados
  apps/tenancy/    barberías, sedes, membresías, roles y matriz de permisos
  apps/audit/      registro de auditoría solo-agregar
  apps/legal/      documentos legales versionados y aceptaciones
  apps/catalog/    servicios
  apps/staff/      barberos y reglas de comisión
  apps/clients/    clientes, duplicados, perfil y anonimización
  apps/inventory/  productos, categorías, insumos y movimientos de stock
  apps/cash/       cajas por sede, libro de movimientos y arqueo
  apps/sales/      comandas, cierre con copia de precio, costo y comisión, y pagos
  apps/receivables/ fiados y abonos
  apps/alerts/     alertas automáticas (comando generar_alertas para cron)
  apps/reports/    reportes, tablero y exportación a Excel (solo lecturas)
  tests/           pruebas (pytest se corre desde backend/)
  requirements/    dependencias fijadas
frontend/
  templates/       plantillas de Django
  static/          marca, fuentes y librerías de terceros con su licencia
docs/              arquitectura y decisiones
```

## Pendiente de marca

`frontend/static/brand/icon.svg` es provisional. Faltan `favicon.ico` (32 px), `apple-touch-icon.png` (180 px) e íconos de 192 y 512 px cuando exista el logo definitivo.

Reglas de trabajo: ver [AGENTS.md](AGENTS.md).
