"""Inicio de sesión y pantallas de cuenta con el diseño de Login.dc.html."""

import pytest
from django.urls import reverse

from apps.accounts.forms import HONEYPOT_FIELD
from apps.tenancy.roles import Role
from tests.frontend.html_support import elements

pytestmark = pytest.mark.django_db


def test_el_login_muestra_la_foto_y_su_credito(client):
    page = client.get(reverse("account_login")).content.decode()
    assert "img/login-barbero.webp" in page
    assert "Foto: Tim Collins Photography" in page
    assert "Gestión ejecutiva para barberías" in page


def test_un_login_fallido_muestra_el_error_con_su_icono(client):
    page = client.post(reverse("account_login"), {"login": "nadie@example.com", "password": "incorrecta"})
    html = page.content.decode()
    assert 'class="form-error"' in html and "lucide-circle-alert" in html


def test_registro_recuperacion_y_2fa_comparten_el_diseno(client, legal_documents, make_shop, make_member):
    for url_name in ("account_signup", "account_reset_password"):
        assert "img/login-barbero.webp" in client.get(reverse(url_name)).content.decode()

    client.force_login(make_member("dueno@example.com", make_shop("a"), Role.OWNER))  # sin 2FA: debe activarlo
    activation = client.get(reverse("mfa_activate_totp"), follow=True)  # antes pide confirmar la contraseña
    assert "img/login-barbero.webp" in activation.content.decode()


def test_el_campo_trampa_sigue_oculto_en_el_registro(client, legal_documents):
    page = client.get(reverse("account_signup")).content.decode()
    [trap] = [attrs for tag, attrs, _ in elements(page) if tag == "input" and attrs.get("name") == HONEYPOT_FIELD]
    assert "hidden" in trap
