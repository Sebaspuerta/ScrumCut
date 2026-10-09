"""Desarrollo local. Los secretos igual se leen del entorno (.env), sin valores por defecto."""

from .base import *  # noqa: F403

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
