"""Hallazgo S4: ni el login ni su bloqueo revelan si una cuenta existe o está inactiva (fase R6)."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.adapter import LOCKOUT_MESSAGE, WRONG_CREDENTIALS
from apps.accounts.models import User
from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

ACTIVE, INACTIVE, MISSING = "activo@example.com", "inactivo@example.com", "nadie@example.com"
AXES_FAILURE_LIMIT = 5
ATTEMPTS = {
    "inactiva con su contraseña": (INACTIVE, TEST_PASSWORD),
    "inactiva con otra contraseña": (INACTIVE, "incorrecta"),
    "activa con otra contraseña": (ACTIVE, "incorrecta"),
    "inexistente": (MISSING, "incorrecta"),
}


@pytest.fixture(autouse=True)
def accounts(make_shop, make_member):
    shop = make_shop("a")
    make_member(ACTIVE, shop, Role.CASHIER)
    make_member(INACTIVE, shop, Role.CASHIER)
    User.objects.filter(email=INACTIVE).update(is_active=False)


def _login(client: Client, email: str, password: str):
    return client.post(reverse("account_login"), {"login": email, "password": password})


def _from_own_ip(number: int) -> Client:
    """Cada caso desde su IP: el límite por IP de allauth no mezcla los casos."""
    return Client(REMOTE_ADDR=f"198.51.100.{number}")


def test_la_cuenta_inactiva_recibe_el_mismo_error_que_cualquier_intento_fallido():
    responses = {case: _login(_from_own_ip(n), *attempt) for n, (case, attempt) in enumerate(ATTEMPTS.items())}

    assert {case: response.status_code for case, response in responses.items()} == dict.fromkeys(ATTEMPTS, 200)
    errors = {case: response.context["form"].errors for case, response in responses.items()}
    assert errors == dict.fromkeys(ATTEMPTS, {"__all__": [WRONG_CREDENTIALS]})
    assert all("_auth_user_id" not in response.wsgi_request.session for response in responses.values())


def test_la_pantalla_de_cuenta_inactiva_ya_no_existe(client):
    assert client.get("/cuenta/inactive/").status_code == 404


def test_la_contrasena_correcta_de_una_cuenta_inactiva_cuenta_como_fallo_para_axes():
    client = _from_own_ip(20)
    for _ in range(AXES_FAILURE_LIMIT - 1):
        _login(client, INACTIVE, TEST_PASSWORD)

    response = _login(client, INACTIVE, TEST_PASSWORD)

    assert response.status_code == 429
    assert LOCKOUT_MESSAGE in response.content.decode()


def _lockout_page(number: int, email: str) -> str:
    client = _from_own_ip(number)
    responses = [_login(client, email, "incorrecta") for _ in range(AXES_FAILURE_LIMIT)]
    assert responses[-1].status_code == 429
    return responses[-1].content.decode()


def test_la_pagina_de_bloqueo_es_la_misma_para_cuenta_existente_inexistente_e_inactiva():
    pages = [_lockout_page(30 + n, email) for n, email in enumerate((ACTIVE, MISSING, INACTIVE))]

    assert pages[0] == pages[1] == pages[2]
    assert LOCKOUT_MESSAGE in pages[0]
    assert ACTIVE not in pages[0] and "bloquead" not in pages[0].lower()


def test_tras_el_bloqueo_el_login_repite_el_mismo_mensaje_aun_con_la_contrasena_correcta():
    client = _from_own_ip(40)
    for _ in range(AXES_FAILURE_LIMIT):
        _login(client, ACTIVE, "incorrecta")

    response = _login(client, ACTIVE, TEST_PASSWORD)

    assert LOCKOUT_MESSAGE in response.content.decode()
    assert "_auth_user_id" not in client.session
