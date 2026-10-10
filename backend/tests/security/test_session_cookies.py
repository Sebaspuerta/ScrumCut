"""Punto 1: la sesión vive en una cookie del servidor que JavaScript no puede leer."""

import pytest
from django.urls import reverse

from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


def test_la_cookie_de_csrf_es_httponly_y_samesite_lax(client):
    cookie = client.get(reverse("account_login")).cookies["csrftoken"]
    assert (cookie["httponly"], cookie["samesite"]) == (True, "Lax")


def test_la_cookie_de_sesion_es_httponly_y_samesite_lax(client, make_shop, make_member):
    make_member("barbero@example.com", make_shop("a"), Role.BARBER)
    response = client.post(reverse("account_login"), {"login": "barbero@example.com", "password": TEST_PASSWORD})
    cookie = response.cookies["sessionid"]
    assert (cookie["httponly"], cookie["samesite"]) == (True, "Lax")


def test_la_pagina_no_entrega_tokens_al_navegador(client, make_shop, make_member):
    client.force_login(make_member("barbero@example.com", make_shop("a"), Role.BARBER))
    assert "token" not in client.get(reverse("home")).content.decode().lower()
