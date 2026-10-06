# ScrumCut

Software de gestión para barberías, por [ScrumTech Solutions](https://www.instagram.com/scrumtech_solutions/).
Multi-barbería, 100 % web, con agenda, comandas, caja, inventario, fiados y reportes gerenciales.

Estado: **fase 0 (fundaciones)**: identidad segura, multi-barbería, auditoría y base legal.

## Stack

Django 6 · PostgreSQL (Row-Level Security por barbería) · django-allauth (correo verificado + 2FA) · django-axes · Argon2.

## Arranque local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env        # completa los valores; ninguno tiene valor por defecto
set -a && source .env && set +a
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
pre-commit install
```

## Estructura

```
config/            settings por ambiente (base, dev, test, prod) y lectura de entorno
apps/core/         modelos base, contexto de barbería activa, operación RLS
apps/accounts/     usuario por correo, 2FA obligatorio para roles privilegiados
apps/tenancy/      barberías, sedes, membresías, roles y matriz de permisos
apps/audit/        registro de auditoría solo-agregar
apps/legal/        documentos legales versionados y aceptaciones
docs/              arquitectura y decisiones
```

## Pendiente de marca

`static/brand/icon.svg` es provisional. Faltan `favicon.ico` (32 px), `apple-touch-icon.png` (180 px) e íconos de 192 y 512 px cuando exista el logo definitivo.

Reglas de trabajo: ver [CLAUDE.md](CLAUDE.md).
