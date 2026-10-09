"""La app no arranca sin la clave de cifrado de datos personales, ni con una inválida.

Corre Django en un proceso aparte con settings de producción, que no leen `.env`,
y variables ficticias para todo lo demás.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FAKE_PROD_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "SECRET_KEY": "solo-prueba-" + "x" * 60,
    "ALLOWED_HOSTS": "app.example.test",
    "DATABASE_URL": "postgres://ficticio:ficticio@localhost:5432/ficticio",
    "ADMIN_URL": "ruta-ficticia",
    "CSRF_TRUSTED_ORIGINS": "https://app.example.test",
    "EMAIL_HOST": "smtp.example.test",
    "EMAIL_HOST_USER": "ficticio",
    "EMAIL_HOST_PASSWORD": "ficticio",
    "DEFAULT_FROM_EMAIL": "no-reply@example.test",
    "FIELD_HASH_KEY": "clave-hash-ficticia",
}


def _start_django(**overrides: str | None) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if not key.startswith("FIELD_")}
    env.update(FAKE_PROD_ENV)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(  # noqa: S603 — comando fijo, sin entrada externa
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_arranca_con_las_claves_correctas():
    result = _start_django(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("missing", ["FIELD_ENCRYPTION_KEY", "FIELD_HASH_KEY"])
def test_no_arranca_sin_una_clave(missing):
    keys = {"FIELD_ENCRYPTION_KEY": Fernet.generate_key().decode(), missing: None}
    result = _start_django(**keys)
    assert result.returncode != 0
    assert missing in result.stderr


def test_no_arranca_con_una_clave_de_cifrado_invalida():
    result = _start_django(FIELD_ENCRYPTION_KEY="no-es-una-clave-fernet")
    assert result.returncode != 0
    assert "Fernet key" in result.stderr
