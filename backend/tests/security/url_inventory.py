"""Inventario de las vistas del proyecto para las pruebas de protección (punto 2 de la lista)."""

import re

from django.conf import settings
from django.urls import URLResolver, get_resolver

# Fuera del inventario, con su motivo.
ALLAUTH_MODULE = "allauth."  # login, registro, recuperación y 2FA: sus límites y mensajes se prueban aparte
ADMIN_PREFIX = settings.ADMIN_URL.strip("/") + "/"  # admin de Django: exige is_staff con su propio login

PUBLIC_VIEWS = {
    "health": "Monitoreo: responde un JSON fijo sin datos.",
    "legal_document": "Los documentos legales se leen antes de registrarse.",
}

LOGIN_ONLY_VIEWS = {
    "home": "Portada: no muestra datos de negocio.",
    "logout_everywhere": "Actúa sobre la propia cuenta, no sobre datos de una barbería.",
}

_SAMPLES = {"int": "1", "uuid": "00000000-0000-0000-0000-000000000000"}


def _walk(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            yield prefix + str(pattern.pattern), pattern.name, pattern.callback


def sample_path(route: str) -> str:
    """Una ruta concreta para pedir la vista: cada parámetro recibe un valor de ejemplo."""
    return "/" + re.sub(r"<(?:(\w+):)?\w+>", lambda match: _SAMPLES.get(match.group(1), "x"), route)


def project_views() -> list[tuple[str, str, object]]:
    return [
        (route, name, view)
        for route, name, view in _walk(get_resolver().url_patterns)
        if not route.startswith(ADMIN_PREFIX) and not view.__module__.startswith(ALLAUTH_MODULE)
    ]
