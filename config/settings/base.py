"""Configuración común. Los ambientes extienden este archivo (dev, test, prod)."""

from datetime import timedelta
from pathlib import Path

import dj_database_url

from config import env

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env.require("SECRET_KEY")
# Cifrado de datos personales (apps/core/crypto.py). Rotarlas exige recifrar.
FIELD_ENCRYPTION_KEY = env.require("FIELD_ENCRYPTION_KEY")
FIELD_HASH_KEY = env.require("FIELD_HASH_KEY")
DEBUG = False
ALLOWED_HOSTS = env.as_list("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "axes",
    "apps.core",
    "apps.accounts",
    "apps.tenancy",
    "apps.audit",
    "apps.legal",
    "apps.catalog",
    "apps.staff",
    "apps.clients",
    "apps.inventory",
    "apps.cash",
    "apps.sales",
    "apps.receivables",
    "apps.alerts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.tenancy.middleware.ActiveBarbershopMiddleware",
    "apps.accounts.middleware.RequireMFAForPrivilegedRolesMiddleware",
    # axes debe ir al final.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.csp",
            ],
        },
    },
]

DATABASES = {"default": dj_database_url.parse(env.require("DATABASE_URL"), conn_max_age=60)}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Identidad -------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# allauth: login por correo verificado, sin nombre de usuario.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
# Invalida el enlace de recuperación si el correo de la cuenta cambia.
ACCOUNT_PASSWORD_RESET_TOKEN_GENERATOR = "allauth.account.forms.EmailAwarePasswordResetTokenGenerator"  # noqa: S105  # nosec B105
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hora
ACCOUNT_RATE_LIMITS = {
    "login": "20/m/ip",
    "login_failed": "5/15m/ip,5/15m/key",
    "signup": "10/h/ip",
    "reset_password": "5/h/ip,3/h/key",  # nosec B105
    "reset_password_from_key": "10/h/ip",  # nosec B105
    "confirm_email": "3/h/key",
}

MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
MFA_TOTP_ISSUER = "ScrumCut"

# axes: bloqueo por combinación usuario + IP para que un atacante no pueda
# bloquear al dueño real desde otra red (falla de la v1).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_FORM_FIELD = "login"

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"

# --- Sesión y cookies ------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 12
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# --- Cabeceras -------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_CSP = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "<CSP_NONCE_SENTINEL>"],
    "style-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "font-src": ["'self'"],
    "connect-src": ["'self'"],
    "frame-ancestors": ["'none'"],
    "form-action": ["'self'"],
    "base-uri": ["'self'"],
    "object-src": ["'none'"],
}

# --- Archivos subidos ------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Internacionalización --------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Fotos de productos. En producción las sirve Nginx o un almacenamiento externo, nunca Django.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATICFILES_DIRS = [BASE_DIR / "static"]

ADMIN_URL = env.require("ADMIN_URL")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env.optional("LOG_LEVEL", "INFO")},
}
