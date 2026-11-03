"""Punto 6: ningún secreto del servidor llega al navegador."""

import os

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils.module_loading import import_string

from apps.tenancy.roles import Role
from config import env

pytestmark = pytest.mark.django_db

PUBLIC_PAGES = ["account_login", "account_signup", "account_reset_password"]
LEGAL_SLUGS = ["terminos", "tratamiento-de-datos", "privacidad", "cookies"]
# Un mailer como el de producción, con una contraseña ficticia que se puede buscar en las páginas.
FAKE_MAIL_PASSWORD = "contrasena-smtp-ficticia-" + "x" * 20
SMTP_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {"host": "smtp.example.test", "username": "ficticio", "password": FAKE_MAIL_PASSWORD},
    }
}


def _mail_password() -> str:
    """La contraseña SMTP del mailer por defecto. Con MAILERS, `settings.EMAIL_HOST_PASSWORD` ya no existe: leerla
    con getattr devolvería "" en silencio. El runner de pruebas deja el mailer sin OPTIONS (locmem)."""
    return settings.MAILERS["default"].get("OPTIONS", {}).get("password", "")


def _secrets() -> list[str]:
    values = [
        settings.SECRET_KEY,
        settings.FIELD_ENCRYPTION_KEY,
        settings.FIELD_HASH_KEY,
        os.environ.get("DATABASE_URL", ""),
        settings.DATABASES["default"].get("PASSWORD", ""),
        _mail_password(),
    ]
    return [value for value in values if value]


def _assert_no_secret(content: str) -> None:
    leaked = [secret[:4] + "…" for secret in _secrets() if secret in content]
    assert leaked == []


def test_las_paginas_publicas_y_el_inicio_no_muestran_secretos(client, legal_documents, make_shop, make_member):
    for name in PUBLIC_PAGES:
        _assert_no_secret(client.get(reverse(name)).content.decode())
    for slug in LEGAL_SLUGS:
        _assert_no_secret(client.get(reverse("legal_document", args=[slug])).content.decode())
    client.force_login(make_member("barbero@example.com", make_shop("a"), Role.BARBER))
    _assert_no_secret(client.get(reverse("home")).content.decode())


@override_settings(MAILERS=SMTP_MAILERS)
def test_la_contrasena_del_correo_cuenta_como_secreto_y_no_llega_a_las_paginas_publicas(client, legal_documents):
    assert FAKE_MAIL_PASSWORD in _secrets()
    with pytest.raises(AssertionError):
        _assert_no_secret(f"<p>{FAKE_MAIL_PASSWORD}</p>")  # el detector la encuentra si se filtra
    for name in PUBLIC_PAGES:
        _assert_no_secret(client.get(reverse(name)).content.decode())


def test_ningun_context_processor_entrega_settings_ni_secretos(make_shop, make_member):
    request = RequestFactory().get("/")
    request.user = make_member("barbero@example.com", make_shop("a"), Role.BARBER)
    for path in settings.TEMPLATES[0]["OPTIONS"]["context_processors"]:
        context = import_string(path)(request)
        assert "settings" not in context, path
        _assert_no_secret(repr({key: str(value) for key, value in context.items()}))


def test_un_secreto_ausente_detiene_el_arranque(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ImproperlyConfigured):
        env.require("SECRET_KEY")


def test_la_salud_no_revela_version_ni_modo(client):
    assert client.get(reverse("health")).json() == {"status": "ok"}
