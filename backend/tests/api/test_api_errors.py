"""Toda /api/v1/ responde los errores con la misma forma: detail, code y field_errors (apps.api.exceptions)."""

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.api.exceptions import GENERIC_MESSAGES
from apps.tenancy.roles import Role
from tests.api.sales_support import open_order, post

pytestmark = pytest.mark.django_db

SHAPE = {"detail", "code", "field_errors"}


def _viewer(member, world) -> Client:
    client = Client()
    client.force_login(member(Role.VIEWER, world.shop, email="consultor@a.test").user)
    return client


def test_cada_tipo_de_error_tiene_la_misma_forma_en_vistas_de_r0_r1_y_r2(world, cashier_client, member):
    viewer = _viewer(member, world)
    errors = {
        "sin sesion": Client().get(reverse("api_navigation")),
        "permiso (R2)": post(viewer, "api_order_create", {}),
        "no existe (R2)": cashier_client.get(reverse("api_order", kwargs={"public_id": uuid.uuid4()})),
        "formato (R0)": post(cashier_client, "api_branch", {}),
        "formato (R1)": cashier_client.patch(
            reverse("api_preferences"), {"theme": "azul"}, content_type="application/json"
        ),
        "regla del service (R2)": post(
            cashier_client,
            "api_order_checkout",
            {"parts": [{"method": "fiado"}]},
            public_id=open_order(world).public_id,
        ),  # fmt: skip
    }

    assert {name: set(response.json()) for name, response in errors.items()} == dict.fromkeys(errors, SHAPE)
    assert errors["no existe (R2)"].json() == {"detail": GENERIC_MESSAGES[404], "code": "not_found", "field_errors": {}}
    assert errors["permiso (R2)"].json()["code"] == "permission_denied"
    assert errors["regla del service (R2)"].json()["code"] == "credit_without_client"


def test_la_validacion_trae_el_mensaje_de_cada_campo(world, cashier_client):
    response = post(cashier_client, "api_cash_open", {"opening_amount": "-5"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid"
    assert list(response.json()["field_errors"]) == ["opening_amount"]


def test_sin_sesion_el_codigo_es_not_authenticated_para_que_la_app_vaya_al_login():
    response = Client().get(reverse("api_navigation"))

    assert response.status_code == 403  # SessionAuthentication no usa 401
    assert response.json() == {"detail": GENERIC_MESSAGES[401], "code": "not_authenticated", "field_errors": {}}


def test_con_sesion_y_sin_permiso_el_codigo_es_permission_denied(world, member):
    response = post(_viewer(member, world), "api_order_create", {})

    assert response.status_code == 403
    assert response.json() == {"detail": GENERIC_MESSAGES[403], "code": "permission_denied", "field_errors": {}}


def test_el_token_csrf_vencido_tiene_su_propio_codigo(world):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(world.cashier.user)

    response = strict.post(reverse("api_branch"), {"sede": "todas"}, content_type="application/json")

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
