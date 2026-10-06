"""Lectura de variables de entorno sin valores por defecto para secretos.

Regla del proyecto: un secreto ausente detiene el arranque. Nunca se agrega
un valor "de respaldo" para SECRET_KEY, credenciales de base de datos o llaves.
"""

import os

from django.core.exceptions import ImproperlyConfigured


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Falta la variable de entorno obligatoria {name}.")
    return value


def optional(name: str, default: str) -> str:
    """Solo para valores que no son secretos (zona horaria, nivel de log...)."""
    return os.environ.get(name, default).strip() or default


def as_list(name: str) -> list[str]:
    return [item.strip() for item in require(name).split(",") if item.strip()]


def as_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default
