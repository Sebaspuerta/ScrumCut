"""Punto 4: login y recuperación con límite de intentos, y el mismo mensaje exista o no el correo."""

import pytest
from django.core import mail
from django.urls import reverse

from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def cashier(make_shop, make_member):
    return make_member("cajero@example.com", make_shop("a"), Role.CASHIER)


def test_cinco_intentos_fallidos_bloquean_el_login(client, cashier):
    url = reverse("account_login")
    for _ in range(5):
        client.post(url, {"login": "cajero@example.com", "password": "incorrecta"})
    response = client.post(url, {"login": "cajero@example.com", "password": TEST_PASSWORD})
    # Aun con la contraseña correcta, la sesión no se abre durante el bloqueo.
    assert response.status_code != 302
    assert "_auth_user_id" not in client.session


def test_fallar_desde_una_ip_no_bloquea_la_cuenta_desde_otra(client, cashier):
    url = reverse("account_login")
    for _ in range(5):
        client.post(url, {"login": "cajero@example.com", "password": "incorrecta"}, REMOTE_ADDR="203.0.113.7")

    response = client.post(url, {"login": "cajero@example.com", "password": TEST_PASSWORD}, REMOTE_ADDR="198.51.100.20")

    assert response.status_code == 302
    assert "_auth_user_id" in client.session


def test_la_recuperacion_respeta_su_limite_por_correo(client, cashier):
    url = reverse("account_reset_password")
    responses = [client.post(url, {"email": "cajero@example.com"}) for _ in range(4)]
    assert [response.status_code for response in responses] == [302, 302, 302, 429]
    assert len(mail.outbox) == 3


def test_el_login_fallido_dice_lo_mismo_exista_o_no_el_correo(client, cashier):
    url = reverse("account_login")
    errors = [
        client.post(url, {"login": email, "password": "incorrecta"}).context["form"].errors
        for email in ("cajero@example.com", "nadie@example.com")
    ]
    assert errors[0] == errors[1]


def test_la_recuperacion_responde_igual_exista_o_no_el_correo(client, cashier):
    url = reverse("account_reset_password")
    responses = [client.post(url, {"email": email}) for email in ("cajero@example.com", "nadie@example.com")]
    assert [(r.status_code, r.url) for r in responses] == [(302, reverse("account_reset_password_done"))] * 2
