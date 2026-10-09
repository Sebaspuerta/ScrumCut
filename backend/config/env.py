"""Lectura de variables de entorno sin valores por defecto para secretos.

Regla del proyecto: un secreto ausente detiene el arranque. Nunca se agrega
un valor "de respaldo" para SECRET_KEY, credenciales de base de datos o llaves.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# El .env de desarrollo vive en la raíz del repositorio, fuera de backend/.
LOCAL_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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


def load_local_dotenv() -> None:
    """Solo desarrollo y pruebas. Sin .env o sin python-dotenv no hace nada; el entorno real manda."""
    if not LOCAL_ENV_FILE.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(LOCAL_ENV_FILE, override=False)
