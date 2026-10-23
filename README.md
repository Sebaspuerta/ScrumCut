# ScrumCut

Software de gestión para barberías, por [ScrumTech Solutions](https://www.instagram.com/scrumtech_solutions/).
Multi-barbería, 100 % web, con agenda, comandas, caja, inventario, fiados y reportes gerenciales.

Estado: **lógica de negocio de MAGNUS portada por completo** (pasos 1 a 9 de `docs/migracion-magnus.md`), sin interfaz todavía. Sobre las fundaciones de la fase 0: identidad segura, multi-barbería, auditoría y base legal.

## Stack

Django 6 · PostgreSQL (Row-Level Security por barbería) · django-allauth (correo verificado + 2FA) · django-axes · Argon2.
API: Django REST Framework + drf-spectacular. App interna: React + TypeScript (Vite, React Router, TanStack Query), en migración desde las plantillas ([decisión](docs/decisiones/frontend-react.md)).

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

### App de React en Windows (PowerShell)

Requiere Node 24. Dos terminales desde la raíz del repositorio:

```powershell
# Terminal 1: Django en 127.0.0.1:8000
.\.venv\Scripts\Activate.ps1
cd backend
python manage.py runserver 127.0.0.1:8000
```

```powershell
# Terminal 2: Vite en localhost:5173
cd frontendpp
npm ci
npm run dev
```

Abre `http://localhost:5173/app/`. Vite atiende `/app/` y pasa todo lo demás (API, `/cuenta/`, estáticos y pantallas en plantillas) a Django, así que el inicio de sesión es el de Django en el mismo origen. No hace falta relajar la CSP: la página de desarrollo la sirve Vite y las de Django conservan la suya.

Compilación para producción (Django la sirve en `/app/` desde `frontend/static/app/`):

```powershell
cd frontendpp
npm run build
```

Si cambia la API, regenera el esquema y los tipos:

```powershell
cd backend
python manage.py spectacular --format openapi-json --validate --fail-on-warn --file ..rontendpp\openapi.json
cd ..rontendpp
npm run gen:types
```

## Pruebas

Desde `backend/`:

```bash
pytest                    # reutiliza la base de pruebas (--reuse-db va en pyproject.toml)
pytest --create-db        # la crea de nuevo: después de agregar o cambiar migraciones
pytest -m "not slow"      # sin las pruebas lentas de migraciones; CI siempre las corre
```

Nunca corras dos procesos de pytest a la vez: comparten la base de pruebas.

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
  apps/api/        API de la app de React (DRF): me, navigation, branch y csrf
  tests/           pruebas (pytest se corre desde backend/)
  requirements/    dependencias fijadas
frontend/
  app/             app de React + TypeScript (Vite); compila en static/app/
  templates/       plantillas de Django
  static/          marca, fuentes y librerías de terceros con su licencia
docs/              arquitectura y decisiones
```

## Pendiente de marca

`frontend/static/brand/icon.svg` es el símbolo compacto de `docs/diseno/marca/` (acento en claro y en oscuro). Faltan `favicon.ico` (32 px), `apple-touch-icon.png` (180 px) e íconos de 192 y 512 px en PNG.

Reglas de trabajo: ver [AGENTS.md](AGENTS.md).
