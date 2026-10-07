"""Pruebas. La integración continua usa PostgreSQL vía DATABASE_URL."""

from pathlib import Path

# pytest-django importa estos settings antes que cualquier conftest.py, así que .env se carga aquí.
# Sin .env (integración continua) o sin python-dotenv no se hace nada; el entorno real manda.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(_ENV_FILE, override=False)

from .base import *  # noqa: E402, F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # solo para acelerar pruebas
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AXES_ENABLED = True
