"""Punto 1: ninguna plantilla ni script del frontend guarda datos en el almacenamiento del navegador.

Incluye el código de la app de React (frontend/app/src, .ts y .tsx) y su compilación (frontend/static/app).
"""

import re

from django.conf import settings

BROWSER_STORAGE = re.compile(r"\b(localStorage|sessionStorage)\b")

# Librerías de terceros que lo usan, con su motivo.
ALLOWED = {
    # Caché del historial de htmx: copias de páginas ya vistas, no credenciales. Se desactiva al montar
    # el frontend (pendiente en docs/arquitectura.md).
    "static/vendor/htmx-2.0.11.min.js": "caché de historial de htmx",
    # La regla de ESLint que prohíbe localStorage y sessionStorage en la app de React los nombra.
    "app/eslint.config.js": "regla de ESLint que los prohíbe",
}

# Dependencias de npm instaladas en cada máquina (no están en el repositorio ni llegan al navegador tal cual):
# lo que sí llega es la compilación, que se revisa en frontend/static/app.
NPM_DEPENDENCIES = "app/node_modules/"
REACT_SOURCES = ("*.ts", "*.tsx")


def _frontend_files():
    frontend = settings.FRONTEND_DIR
    react = [path for pattern in REACT_SOURCES for path in (frontend / "app" / "src").rglob(pattern)]
    for path in [*frontend.rglob("*.html"), *frontend.rglob("*.js"), *react]:
        name = path.relative_to(frontend).as_posix()
        if not name.startswith(NPM_DEPENDENCIES):
            yield name, path


def test_la_revision_incluye_el_codigo_de_la_app_de_react():
    names = {name for name, _ in _frontend_files()}
    assert {"app/src/main.tsx", "app/src/api/client.ts", "app/index.html"} <= names


def test_nada_del_frontend_usa_local_storage_ni_session_storage():
    offenders = [
        name
        for name, path in _frontend_files()
        if name not in ALLOWED and BROWSER_STORAGE.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert offenders == []
