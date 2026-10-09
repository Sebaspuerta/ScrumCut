"""Pruebas. La integración continua usa PostgreSQL vía DATABASE_URL."""

from config.env import load_local_dotenv

# pytest-django importa estos settings antes que cualquier conftest.py, así que .env se carga aquí.
load_local_dotenv()

from .base import *  # noqa: E402, F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # solo para acelerar pruebas
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AXES_ENABLED = True
