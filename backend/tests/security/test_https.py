"""Punto 5: en producción todo va por HTTPS, con HSTS y cookies Secure."""

import importlib
import sys

import pytest

PROD_ONLY_ENV = {
    "CSRF_TRUSTED_ORIGINS": "https://app.example.test",
    "EMAIL_HOST": "smtp.example.test",
    "EMAIL_HOST_USER": "ficticio",
    "EMAIL_HOST_PASSWORD": "ficticio",
    "DEFAULT_FROM_EMAIL": "no-reply@example.test",
}


@pytest.fixture
def prod(monkeypatch):
    """Lee el módulo de settings de producción sin activarlo para el resto de las pruebas."""
    for name, value in PROD_ONLY_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delitem(sys.modules, "config.settings.prod", raising=False)
    return importlib.import_module("config.settings.prod")


def test_produccion_fuerza_https_con_hsts_y_cookies_secure(prod):
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SECURE_HSTS_SECONDS > 0
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert (prod.SESSION_COOKIE_SECURE, prod.CSRF_COOKIE_SECURE) == (True, True)
    assert (prod.SESSION_COOKIE_HTTPONLY, prod.CSRF_COOKIE_HTTPONLY) == (True, True)
