"""Producción. `manage.py check --deploy` debe pasar sin avisos."""

from config import env

from .base import *  # noqa: F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# HSTS gradual: empezar con 86400 (1 día) y subir a 31536000 (1 año)
# cuando el dominio y los subdominios estén estables.
SECURE_HSTS_SECONDS = env.as_int("HSTS_SECONDS", 86400)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
# Entrar a la lista de precarga de los navegadores es difícil de revertir; se
# decide cuando el dominio definitivo lleve meses estable. Aviso silenciado a propósito.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

# IP real del visitante detrás de Cloudflare. Requisito: Nginx acepta tráfico
# solo desde rangos de Cloudflare; si no, esta cabecera se puede falsificar.
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_CF_CONNECTING_IP", "REMOTE_ADDR"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.as_list("CSRF_TRUSTED_ORIGINS")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.require("EMAIL_HOST")
EMAIL_PORT = env.as_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env.require("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env.require("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env.require("DEFAULT_FROM_EMAIL")
