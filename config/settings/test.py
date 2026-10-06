"""Pruebas. La integración continua usa PostgreSQL vía DATABASE_URL."""

from .base import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # solo para acelerar pruebas
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AXES_ENABLED = True
