"""La API solo acepta la sesión de Django, exige CSRF en las escrituras y responde errores genéricos."""

import base64

import pytest
from django.test import Client
from django.urls import reverse

from apps.api.exceptions import GENERIC_MESSAGES, STATUS_CODES
from apps.tenancy.models import Membership
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

READS = ["api_me", "api_navigation", "api_csrf"]


@pytest.mark.parametrize("name", READS)
def test_sin_sesion_las_lecturas_responden_401_o_403(client, name):
    response = client.get(reverse(name))
    assert response.status_code in {401, 403}


def test_sin_sesion_el_cambio_de_sede_responde_401_o_403(client):
    response = client.post(reverse("api_branch"), {"sede": "todas"}, content_type="application/json")
    assert response.status_code in {401, 403}


def test_el_error_es_generico_y_en_espanol(client):
    response = client.get(reverse("api_me"))
    assert response.json() == {
        "detail": GENERIC_MESSAGES[response.status_code],
        "code": STATUS_CODES[response.status_code],
        "field_errors": {},
    }


def test_no_acepta_basic_auth(world):
    credentials = f"{world.cashier.user.email}:{TEST_PASSWORD}".encode()
    header = "Basic " + base64.b64encode(credentials).decode()
    response = Client().get(reverse("api_me"), HTTP_AUTHORIZATION=header)
    assert response.status_code in {401, 403}


def test_un_post_sin_csrf_se_rechaza_y_con_el_token_de_la_api_pasa(world):
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)
    url, body = reverse("api_branch"), {"sede": str(world.branch.public_id)}

    rejected = client.post(url, body, content_type="application/json")
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)

    assert rejected.status_code == 403
    assert accepted.status_code == 200


def test_sin_barberia_activa_me_responde_solo_la_persona_y_navigation_se_niega(client, make_member, make_shop):
    user = make_member("varias@example.com", make_shop("x"), "cashier")
    Membership.objects.filter(user=user).delete()
    client.force_login(user)

    me = client.get(reverse("api_me")).json()

    assert me["user"]["email"] == "varias@example.com"
    assert (me["barbershop"], me["role"], me["permissions"], me["branch"]) == (None, None, [], None)
    assert client.get(reverse("api_navigation")).status_code == 403


def test_no_hay_api_navegable_ni_esquema_publico(owner_client):
    response = owner_client.get(reverse("api_me"), HTTP_ACCEPT="text/html")
    assert response["Content-Type"].startswith("application/json")
    assert owner_client.get("/api/v1/schema/").status_code == 404
