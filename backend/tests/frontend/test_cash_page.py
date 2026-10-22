"""Pantalla de Caja (fase F3): sedes sin mezclar, permisos, arqueo por denominación, nota y consultas."""

from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from apps.cash import services as cash
from apps.cash.models import CashMovement, CashSession
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db

D = Decimal


def _client(membership) -> Client:
    client = Client()
    client.force_login(membership.user)
    return client


def _notices(response) -> str:
    return " ".join(str(message) for message in get_messages(response.wsgi_request))


def _expense(amount="1000"):
    return {"monto": amount, "concepto": "Toallas"}


@pytest.fixture
def norte_session(world):
    norte = Branch.objects.create(name="Norte")
    return cash.open_session(world.owner, scope_of(world.owner, norte), opening_amount=D("10000"))


def test_no_se_mezclan_las_cajas_de_las_sedes(world, norte_session):
    cashier = _client(world.cashier)

    page = cashier.get(reverse("cash_register"))
    url = reverse("cash_movement", args=[norte_session.public_id, "gasto"])

    assert page.context["session"] == world.session
    assert cashier.post(url, _expense()).status_code == 404
    assert not CashMovement.objects.filter(session=norte_session).exists()
    owner = logged_in_with_mfa(world.owner.user)
    owner.post(reverse("switch_branch"), {"sede": "todas"})
    assert owner.get(reverse("cash_register")).context["needs_branch"]


def test_abrir_gastar_retirar_y_cerrar_exigen_su_permiso(world, member, in_shop):
    viewer = _client(member(Role.VIEWER, in_shop))  # ve la caja, pero no la mueve
    session = world.session.public_id

    assert viewer.get(reverse("cash_register")).status_code == 200
    assert viewer.post(reverse("cash_open"), {"base": "0"}).status_code == 403
    for kind in ("gasto", "retiro"):
        assert viewer.post(reverse("cash_movement", args=[session, kind]), _expense()).status_code == 403
    assert viewer.post(reverse("cash_close", args=[session]), {"monedas": "0"}).status_code == 403
    assert _client(world.ana_login).get(reverse("cash_register")).status_code == 403


def _count(**bills) -> dict:
    data = {f"billetes_{bill}": 0 for bill in (100000, 50000, 20000, 10000, 5000, 2000, 1000)}
    return {**data, **{f"billetes_{bill}": count for bill, count in bills.items()}, "monedas": "0"}


def test_el_contado_por_denominaciones_suma_bien(world):
    # world abre con 50 000 y sin ventas: 2 × 20 000 + 1 × 5 000 + 3 × 1 000 + 2 000 en monedas = 50 000.
    data = {**_count(**{"20000": 2, "5000": 1, "1000": 3}), "monedas": "2000"}

    _client(world.cashier).post(reverse("cash_close", args=[world.session.public_id]), data)

    closed = CashSession.objects.get(pk=world.session.pk)
    assert (closed.counted_amount, closed.difference) == (D("50000"), D("0"))


def test_con_diferencia_y_sin_nota_no_cierra(world):
    data = {**_count(), "billetes_20000": 2}  # 40 000 frente a 50 000 esperados

    response = _client(world.cashier).post(reverse("cash_close", args=[world.session.public_id]), data)

    assert CashSession.objects.get(pk=world.session.pk).is_open
    assert "Explica la diferencia" in _notices(response)
    data["nota"] = "Faltaron 10 000 de vueltas"
    _client(world.cashier).post(reverse("cash_close", args=[world.session.public_id]), data)
    assert not CashSession.objects.get(pk=world.session.pk).is_open


def test_despues_de_cerrar_no_se_registran_movimientos(world):
    cashier = _client(world.cashier)
    cashier.post(reverse("cash_close", args=[world.session.public_id]), {**_count(**{"50000": 1})})

    response = cashier.post(reverse("cash_movement", args=[world.session.public_id, "gasto"]), _expense())

    assert not CashMovement.objects.filter(session=world.session).exists()
    assert "cerrada" in _notices(response) or response.status_code == 404


# Sesión, alcance, marco, la caja con su franja, si viene de otro día, movimientos, otros medios y cierres.
CASH_QUERIES = 20


@pytest.mark.parametrize("expenses", [1, 8])
def test_la_caja_no_crece_con_el_numero_de_movimientos(world, django_assert_num_queries, expenses):
    for _ in range(expenses):
        cash.register_manual_movement(
            world.cashier,
            world.session.public_id,
            scope=scope_of(world.cashier),
            kind="gasto",
            amount=D("1000"),
            payment_method="efectivo",
            description="Aseo",
        )
    cashier = _client(world.cashier)

    with django_assert_num_queries(CASH_QUERIES):
        cashier.get(reverse("cash_register"))
