"""Campos de allauth fuera del login (2FA y códigos de recuperación): etiqueta arriba, campo y ayuda debajo."""

import re
import time

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
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


def test_el_qr_del_2fa_lleva_su_superficie_clara_y_las_demas_imagenes_no(client, make_shop, make_member):
    _recently_authenticated(client, make_member("admin@example.com", make_shop("a"), Role.ADMIN))
    page = client.get(reverse("mfa_activate_totp")).content.decode()

    assert re.search(r'<img src="data:image/svg\+xml;base64,[^"]+" alt="[A-Z2-7]+" class="auth-qr">', page)
    assert page.count('class="auth-qr"') == 1


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

    assert f'<a class="button--primary" href="{reverse("react_app")}">Continuar al tablero</a>' in page


@pytest.mark.parametrize(
    ("url_name", "text"),
    [
        ("account_signup", "¿Ya tienes una cuenta?"),
        ("account_reset_password", "¿Olvidaste tu contraseña? Escribe tu correo"),
        ("account_reset_password_done", "Te enviamos un correo."),
        ("account_email_verification_sent", "Te enviamos un correo para verificar tu dirección."),
    ],
)
def test_las_pantallas_de_allauth_tutean(client, legal_documents, url_name, text):
    assert text in client.get(reverse(url_name)).content.decode()


def test_el_2fa_tutea_y_se_llama_verificacion_en_dos_pasos(client, make_shop, make_member):
    _recently_authenticated(client, make_member("admin@example.com", make_shop("a"), Role.ADMIN))
    page = client.get(reverse("mfa_activate_totp")).content.decode()

    assert "escanea este código QR con tu aplicación de autenticación" in page
    assert "Escanee" not in page and "Autenticació " not in page


SUPPORT_TEXTS = {
    "account_reset_password": "Si tienes problemas para restablecer tu contraseña, escríbenos a soporte@example.test.",
    "account_reset_password_done": "Si no te llega en unos minutos, escríbenos a soporte@example.test.",
    "account_email_verification_sent": "Si no te llega en unos minutos, escríbenos a soporte@example.test.",
}


@pytest.mark.parametrize(("url_name", "text"), SUPPORT_TEXTS.items())
def test_recuperar_y_verificar_dan_el_contacto_de_soporte(client, legal_documents, settings, url_name, text):
    settings.SUPPORT_EMAIL = "soporte@example.test"
    assert text in client.get(reverse(url_name)).content.decode()


@pytest.mark.parametrize("url_name", SUPPORT_TEXTS)
def test_sin_contacto_configurado_se_omite_la_frase_de_escribirnos(client, legal_documents, settings, url_name):
    settings.SUPPORT_EMAIL = ""
    assert "escríbenos" not in client.get(reverse(url_name)).content.decode()


def test_confirmar_correo_dice_que_es_tu_correo(client, make_shop, make_member):
    user = make_member("nueva@example.com", make_shop("a"), Role.CASHIER)
    address = EmailAddress.objects.get(user=user)
    address.verified = False
    address.save()
    key = EmailConfirmationHMAC(address).key

    page = client.get(reverse("account_confirm_email", args=[key])).content.decode()

    assert 'Confirma que <a href="mailto:nueva@example.com">nueva@example.com</a> es tu correo.' in page
