"""Punto 14: solo cookies esenciales, por eso no hay banner de consentimiento."""

import pytest
from django.urls import reverse

from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

PUBLIC_URLS = [
    ("account_login", []),
    ("account_signup", []),
    ("account_reset_password", []),
    ("legal_document", ["terminos"]),
    ("legal_document", ["cookies"]),
    ("health", []),
]


def test_una_visita_anonima_solo_recibe_la_cookie_de_csrf(client, legal_documents):
    for name, args in PUBLIC_URLS:
        client.get(reverse(name, args=args))
    assert set(client.cookies) == {"csrftoken"}


def test_al_iniciar_sesion_se_suma_solo_la_de_sesion(client, legal_documents, make_shop, make_member):
    make_member("barbero@example.com", make_shop("a"), Role.BARBER)
    client.post(reverse("account_login"), {"login": "barbero@example.com", "password": TEST_PASSWORD})
    client.get(reverse("home"))
    assert set(client.cookies) == {"csrftoken", "sessionid"}
