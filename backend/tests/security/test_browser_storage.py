"""Punto 1: ninguna plantilla ni script del frontend guarda datos en el almacenamiento del navegador."""

import re

from django.conf import settings

BROWSER_STORAGE = re.compile(r"\b(localStorage|sessionStorage)\b")

# Librerías de terceros que lo usan, con su motivo.
ALLOWED = {
    # Caché del historial de htmx: copias de páginas ya vistas, no credenciales. Se desactiva al montar
    # el frontend (pendiente en docs/arquitectura.md).
    "static/vendor/htmx-2.0.11.min.js": "caché de historial de htmx",
}


def _frontend_files():
    frontend = settings.FRONTEND_DIR
    for path in [*frontend.rglob("*.html"), *frontend.rglob("*.js")]:
        yield path.relative_to(frontend).as_posix(), path


def test_nada_del_frontend_usa_local_storage_ni_session_storage():
    offenders = [
        name
        for name, path in _frontend_files()
        if name not in ALLOWED and BROWSER_STORAGE.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert offenders == []
