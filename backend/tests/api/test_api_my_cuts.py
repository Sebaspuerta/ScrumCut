"""«Mis cortes» en la API: el barbero de la sesión y nada de otro barbero, la comisión copiada al cerrar, el día en
la URL, la sede activa y consultas constantes."""

import pytest
from django.db import connection
from django.db.models import Sum
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.sales import services
from apps.sales.models import OrderItem
from apps.tenancy.roles import Role
from tests.api.sales_support import choose_branch, open_order, post
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

ZERO = {"orders": 0, "cuts": 0, "production": "0.00", "commission": "0.00"}


def _login(membership) -> Client:
    client = Client()
    client.force_login(membership.user)
    return client


def _cut(world, barber, *, actor=None, branch=None) -> None:
    """Un corte cobrado por Nequi con el cobro rápido de Django."""
    actor = actor or world.cashier
    scope = scope_of(actor, branch or world.branch)
    services.quick_register(actor, scope, barber=barber.public_id, method="nequi", service=world.corte.public_id)


def _shared_order(world, cashier_client) -> None:
    """Una comanda con un corte de Ana y una barba de Beto, cobrada por Nequi."""
    order = open_order(world)
    scope = scope_of(world.cashier)
    services.add_item(
        world.cashier, order.public_id, scope=scope, service=world.barba.public_id, barber=world.beto.public_id
    )
    post(cashier_client, "api_order_checkout", {"parts": [{"method": "nequi"}]}, public_id=order.public_id)


def _commission_copied(barber) -> str:
    return str(OrderItem.objects.filter(barber=barber).aggregate(total=Sum("commission_amount"))["total"])


def test_el_barbero_ve_hoy_y_el_mes_con_la_comision_copiada_al_cerrar(world):
    for _ in range(2):
        _cut(world, world.ana)
    _cut(world, world.beto)

    data = _login(world.ana_login).get(reverse("api_my_cuts")).json()

    expected = {"orders": 2, "cuts": 2, "production": "50000.00", "commission": _commission_copied(world.ana)}
    assert data["barber"] == "Ana"
    assert data["today"] == data["month"] == expected
    assert expected["commission"] == "20000.00"  # el 40 % de Ana, copiado en cada línea
    assert [(row["items"], row["production"], row["commission"]) for row in data["results"]] == [
        ("Corte", "25000.00", "10000.00"),
        ("Corte", "25000.00", "10000.00"),
    ]


def test_el_barbero_a_no_ve_nada_del_barbero_b_ni_pasando_su_id(world, cashier_client):
    _shared_order(world, cashier_client)
    _cut(world, world.beto)
    beto_id = str(world.beto.public_id)

    ana = _login(world.ana_login).get(reverse("api_my_cuts"), {"barbero": beto_id, "barber": beto_id}).json()
    beto = _login(world.beto_login).get(reverse("api_my_cuts")).json()

    assert ana["barber"] == "Ana"
    assert [(row["items"], row["production"], row["commission"]) for row in ana["results"]] == [
        ("Corte", "25000.00", "10000.00")
    ]
    assert ana["today"] == {"orders": 1, "cuts": 1, "production": "25000.00", "commission": "10000.00"}
    shared = ana["results"][0]["number"]
    assert [(row["items"], row["commission"]) for row in beto["results"] if row["number"] == shared] == [
        ("Barba", "7500.00")
    ]
    assert beto["today"]["commission"] == _commission_copied(world.beto) == "20000.00"


def test_el_dia_va_en_la_url_y_uno_invalido_vuelve_a_hoy(world):
    _cut(world, world.ana)
    client = _login(world.ana_login)

    other_day = client.get(reverse("api_my_cuts"), {"fecha": "2020-01-01"}).json()
    invalid = client.get(reverse("api_my_cuts"), {"fecha": "ayer"}).json()

    assert (other_day["day"], other_day["results"], other_day["today"]["cuts"]) == ("2020-01-01", [], 1)
    assert len(invalid["results"]) == 1


def test_solo_cuenta_la_sede_activa(world, norte):
    _cut(world, world.ana)
    _cut(world, world.ana, actor=world.owner, branch=norte)
    client = _login(world.ana_login)

    choose_branch(client, world.branch)
    centro = client.get(reverse("api_my_cuts")).json()
    choose_branch(client, norte)
    in_norte = client.get(reverse("api_my_cuts")).json()

    assert (centro["today"]["cuts"], len(centro["results"])) == (1, 1)
    assert (in_norte["today"]["cuts"], len(in_norte["results"])) == (1, 1)
    assert centro["results"][0]["number"] != in_norte["results"][0]["number"]


@pytest.mark.parametrize("role", [Role.CASHIER, Role.VIEWER])
def test_sin_barbero_propio_no_hay_cortes(world, member, role):
    _cut(world, world.ana)
    login = world.cashier if role == Role.CASHIER else member(role, world.shop)

    data = _login(login).get(reverse("api_my_cuts")).json()

    assert (data["barber"], data["today"], data["month"], data["results"]) == (None, ZERO, ZERO, [])


def test_sin_sesion_no_responde(client):
    assert client.get(reverse("api_my_cuts")).status_code in {401, 403}


def _queries(client: Client) -> int:
    client.get(reverse("api_my_cuts"))  # la primera petición puede guardar la sede en la sesión
    with CaptureQueriesContext(connection) as context:
        assert client.get(reverse("api_my_cuts")).status_code == 200
    return len(context.captured_queries)


def test_no_crece_en_consultas(world):
    client = _login(world.ana_login)
    _cut(world, world.ana)
    with_one = _queries(client)

    for _ in range(4):
        _cut(world, world.ana)

    assert _queries(client) == with_one
