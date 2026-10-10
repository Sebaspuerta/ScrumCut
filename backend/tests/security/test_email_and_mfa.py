"""Punto 3: correo verificado para entrar y 2FA obligatorio para Dueño y Administrador."""

import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD
from tests.security.url_inventory import PUBLIC_VIEWS, project_views, sample_path

pytestmark = pytest.mark.django_db

# /cuenta/ queda abierta a propósito: ahí se configura el 2FA.
BUSINESS_PATHS = [
    sample_path(route)
    for route, name, _ in project_views()
    if name not in PUBLIC_VIEWS and not route.startswith("cuenta/")
]


def test_con_el_correo_sin_verificar_no_se_inicia_sesion(client, make_shop, make_member):
    make_member("cajero@example.com", make_shop("a"), Role.CASHIER)
    EmailAddress.objects.filter(email="cajero@example.com").update(verified=False)

    client.post(reverse("account_login"), {"login": "cajero@example.com", "password": TEST_PASSWORD})

    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN])
def test_dueno_o_administrador_sin_2fa_no_entra_a_ninguna_vista_de_negocio(client, make_shop, make_member, role):
    client.force_login(make_member("jefe@example.com", make_shop("a"), role))
    for path in BUSINESS_PATHS:
        response = client.get(path)
        assert (response.status_code, response.url) == (302, reverse("mfa_activate_totp")), path


def test_el_barbero_entra_sin_2fa_obligatorio(client, make_shop, make_member):
    client.force_login(make_member("barbero@example.com", make_shop("a"), Role.BARBER))
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert response.wsgi_request.barbershop.slug == "a"
