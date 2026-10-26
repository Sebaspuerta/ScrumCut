"""Comandas en la API: alcance de sede, permisos por rol, "todas" sin escrituras, precio de la sede y CSRF."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.cash.board import CLOSINGS_PAGE_SIZE
from apps.catalog.branch_prices import set_branch_price
from apps.sales.board import PAGE_SIZE
from apps.sales.forms import MAX_LINE_QUANTITY
from apps.sales.models import Order, OrderStatus
from apps.sales.services.checkout import MAX_PARTS
from apps.tenancy.branch_scope import WRITE_NEEDS_ONE_BRANCH
from apps.tenancy.roles import Role
from tests.api.sales_support import choose_branch, open_order, post
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db


def _as(member_fixture, world, role: Role) -> Client:
    client = Client()
    client.force_login(member_fixture(role, world.shop, email=f"{role}-api@a.test").user)
    return client


def test_la_lista_trae_las_abiertas_con_su_conteo_y_el_detalle_sus_lineas(world, cashier_client):
    order = open_order(world, client=world.laura.public_id)

    listing = cashier_client.get(reverse("api_orders")).json()
    detail = cashier_client.get(reverse("api_order", kwargs={"public_id": order.public_id})).json()

    assert [row["number"] for row in listing["results"]] == [order.number]
    assert {tab["value"]: tab["count"] for tab in listing["tabs"]} == {"abiertas": 1, "cerradas": 0, "anuladas": 0}
    assert detail["total"] == "25000.00"
    assert [(line["name"], line["barber"], line["unit_price"]) for line in detail["lines"]] == [
        ("Corte", "Ana", "25000.00")
    ]
    assert detail["client"]["phone"] == "300 *** 4567"  # nunca el celular completo
    assert detail["actions"] == {"edit": True, "discount": True, "checkout": True, "cancel": True}


def test_el_filtro_de_fecha_muestra_las_cerradas_de_ese_dia(world, cashier_client):
    order = open_order(world)
    post(cashier_client, "api_order_checkout", {"parts": [{"method": "nequi"}]}, public_id=order.public_id)

    today = cashier_client.get(reverse("api_orders"), {"estado": "cerradas"}).json()
    other_day = cashier_client.get(reverse("api_orders"), {"estado": "cerradas", "fecha": "2020-01-01"}).json()

    assert [row["number"] for row in today["results"]] == [order.number]
    assert today["summary"]["other"] == "25000.00"
    assert (other_day["results"], other_day["day"]) == ([], "2020-01-01")


def test_el_cajero_de_centro_no_ve_ni_cobra_ni_anula_una_comanda_de_norte(world, norte, cashier_client):
    order = open_order(world, actor=world.owner, branch=norte)
    url_kwargs = {"public_id": order.public_id}

    assert cashier_client.get(reverse("api_order", kwargs=url_kwargs)).status_code == 404
    assert post(cashier_client, "api_order_checkout", {"parts": [{"method": "nequi"}]}, **url_kwargs).status_code == 404
    assert post(cashier_client, "api_order_cancel", {"reason": "x"}, **url_kwargs).status_code == 404
    assert cashier_client.get(reverse("api_orders")).json()["results"] == []
    assert Order.objects.get(pk=order.pk).status == OrderStatus.OPEN


def test_el_consultor_lee_pero_no_crea(world, member):
    viewer = _as(member, world, Role.VIEWER)

    assert viewer.get(reverse("api_orders")).status_code == 200
    assert post(viewer, "api_order_create", {}).status_code == 403


def test_el_barbero_ve_solo_sus_comandas(world):
    order = open_order(world)  # la abre el cajero con Ana como barbera
    ana, beto = Client(), Client()
    ana.force_login(world.ana_login.user)
    beto.force_login(world.beto_login.user)

    assert [row["number"] for row in ana.get(reverse("api_orders")).json()["results"]] == [order.number]
    assert beto.get(reverse("api_orders")).json()["results"] == []
    assert beto.get(reverse("api_order", kwargs={"public_id": order.public_id})).status_code == 404


def test_el_cajero_no_anula_una_cerrada_sin_comandas_anular(world, cashier_client):
    order = open_order(world)
    post(cashier_client, "api_order_checkout", {"parts": [{"method": "nequi"}]}, public_id=order.public_id)

    detail = cashier_client.get(reverse("api_order", kwargs={"public_id": order.public_id})).json()
    response = post(cashier_client, "api_order_cancel", {"reason": "Error"}, public_id=order.public_id)

    assert detail["actions"]["cancel"] is False
    assert response.status_code == 403
    assert Order.objects.get(pk=order.pk).status == OrderStatus.CLOSED


def test_en_todas_las_sedes_no_se_escribe_y_el_mensaje_pide_elegir_una(world, norte, owner_client):
    assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200

    response = post(owner_client, "api_order_create", {"lines": [{"service": str(world.corte.public_id)}]})
    catalog = owner_client.get(reverse("api_order_catalog")).json()

    assert response.status_code == 400
    assert response.json()["detail"] == WRITE_NEEDS_ONE_BRANCH
    assert catalog["needs_branch"] is True
    assert not Order.objects.exists()


def test_crear_usa_el_precio_vigente_de_la_sede(world, norte, owner_client):
    set_branch_price(world.owner, world.corte, scope=scope_of(world.owner, norte), price=Decimal("30000"))
    line = {"service": str(world.corte.public_id), "barber": str(world.ana.public_id), "quantity": 2}
    choose_branch(owner_client, norte)

    created = post(owner_client, "api_order_create", {"lines": [line], "unit_price": "1"})
    catalog = owner_client.get(reverse("api_order_catalog")).json()

    assert created.status_code == 201
    assert (created.json()["lines"][0]["unit_price"], created.json()["total"]) == ("30000.00", "60000.00")
    assert {item["name"]: item["price"] for item in catalog["services"]}["Corte"] == "30000.00"
    assert {item["name"]: item["stock"] for item in catalog["products"]} == {"Cera": 3}


def test_una_linea_invalida_no_deja_la_comanda_a_medias(world, cashier_client):
    response = post(cashier_client, "api_order_create", {"lines": [{"service": str(world.laura.public_id)}]})

    assert response.status_code == 400
    assert response.json()["field_errors"] == {"lines": ["El servicio no existe o está inactivo."]}
    assert not Order.objects.exists()


def test_el_dinero_no_se_acepta_como_float(world, cashier_client):
    order = open_order(world)

    response = post(cashier_client, "api_order_discount", {"amount": 1000.5, "reason": "x"}, public_id=order.public_id)

    assert response.status_code == 400
    assert "amount" in response.json()["field_errors"]


def test_las_escrituras_exigen_csrf(world):
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)

    rejected = post(client, "api_order_create", {})
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(reverse("api_order_create"), {}, content_type="application/json", HTTP_X_CSRFTOKEN=token)

    assert rejected.status_code == 403
    assert accepted.status_code == 201


def test_la_busqueda_de_clientes_solo_trae_nombre_y_celular_enmascarado(world, cashier_client):
    found = cashier_client.get(reverse("api_client_search"), {"q": "laura"}).json()

    assert found == [{"id": str(world.laura.public_id), "name": "Laura Gómez", "phone": "300 *** 4567"}]
    assert cashier_client.get(reverse("api_client_search")).json() == []


def test_los_topes_y_el_tamano_de_pagina_los_da_el_servidor(world, cashier_client):
    catalog = cashier_client.get(reverse("api_order_catalog")).json()
    listing = cashier_client.get(reverse("api_orders")).json()
    closings = cashier_client.get(reverse("api_cash_closings")).json()

    assert (catalog["max_parts"], catalog["max_quantity"]) == (MAX_PARTS, MAX_LINE_QUANTITY)
    assert (listing["page_size"], closings["page_size"]) == (PAGE_SIZE, CLOSINGS_PAGE_SIZE)


def test_una_cantidad_sobre_el_tope_se_rechaza(world, cashier_client):
    line = {"service": str(world.corte.public_id), "quantity": MAX_LINE_QUANTITY + 1}

    response = post(cashier_client, "api_order_create", {"lines": [line]})

    assert response.status_code == 400
    assert "lines" in response.json()["field_errors"]
