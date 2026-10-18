"""Pruebas. La integración continua usa PostgreSQL vía DATABASE_URL."""

from config.env import load_local_dotenv

# pytest-django importa estos settings antes que cualquier conftest.py, así que .env se carga aquí.
load_local_dotenv()

from .base import *  # noqa: E402, F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # solo para acelerar pruebas
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AXES_ENABLED = True

# Una espera por bloqueo (por ejemplo, otra corrida de pytest sobre la misma base) falla en 10 s
# con "canceling statement due to lock timeout", en vez de dejar la suite detenida. Cualquier
# otra sentencia que pase de 30 s también se cancela.
LOCK_TIMEOUT_MS = 10_000
STATEMENT_TIMEOUT_MS = 30_000
DATABASES["default"].setdefault("OPTIONS", {})["options"] = (
    f"-c lock_timeout={LOCK_TIMEOUT_MS} -c statement_timeout={STATEMENT_TIMEOUT_MS}"
)
