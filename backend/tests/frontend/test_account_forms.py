"""Campos de allauth fuera del login (2FA y códigos de recuperación): etiqueta arriba, campo y ayuda debajo."""

import re
import time

import pytest
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
from django.urls import reverse

from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db


def _recently_authenticated(client, user):
    """Estas pantallas piden haber confirmado la contraseña hace poco."""
    client.force_login(user)
    session = client.session
    session["account_authentication_methods"] = [{"method": "password", "at": time.time(), "email": user.email}]
    session.save()


def _field(page: str, field_id: str, control: str) -> re.Match | None:
    """El campo completo: <div class="auth-field">, su etiqueta y luego el control, sin el <p> de allauth."""
    pattern = rf'<div class="auth-field">\s*<label for="{field_id}">.*?</label>\s*<{control}[^>]*id="{field_id}"'
    return re.search(pattern, page, re.DOTALL)


def test_el_secreto_del_2fa_va_en_columna_con_su_ayuda_debajo(client, make_shop, make_member):
    _recently_authenticated(client, make_member("admin@example.com", make_shop("a"), Role.ADMIN))
    page = client.get(reverse("mfa_activate_totp")).content.decode()

    field = _field(page, "authenticator_secret", "input")
    assert field, "el secreto no está en un .auth-field con la etiqueta encima"
    assert re.match(r'[^<]*>\s*<div class="auth-field__help">', page[field.end() :])


def test_los_codigos_de_recuperacion_van_en_columna(client, make_shop, make_member):
    owner = make_member("dueno@example.com", make_shop("a"), Role.OWNER)
    TOTP.activate(owner, generate_totp_secret())
    RecoveryCodes.activate(owner)
    _recently_authenticated(client, owner)

    page = client.get(reverse("mfa_view_recovery_codes")).content.decode()

    assert _field(page, "recovery_codes", "textarea"), "los códigos no están en un .auth-field con la etiqueta encima"


def test_los_codigos_de_recuperacion_llevan_al_tablero_con_el_boton_principal(client, make_shop, make_member):
    owner = make_member("dueno@example.com", make_shop("a"), Role.OWNER)
    TOTP.activate(owner, generate_totp_secret())
    RecoveryCodes.activate(owner)
    _recently_authenticated(client, owner)

    page = client.get(reverse("mfa_view_recovery_codes")).content.decode()

    assert f'<a class="button--primary" href="{reverse("home")}">Continuar al tablero</a>' in page
