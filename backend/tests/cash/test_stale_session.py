"""Caja abierta desde otro día (fase F3b): no recibe ni entrega efectivo hasta cerrarla y abrir la de hoy."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashSession
from apps.cash.selectors import expected_cash
from apps.sales import services as sales
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

D = Decimal
STALE = "La caja viene de otro día"


def _age(world, days: int) -> CashSession:
    CashSession.objects.filter(pk=world.session.pk).update(opened_at=timezone.now() - timedelta(days=days))
    return CashSession.objects.get(pk=world.session.pk)


def _order(world):
    scope = scope_of(world.cashier, world.branch)
    order = sales.create_order(world.cashier, scope, barber=world.ana.public_id)
    sales.add_item(world.cashier, order.public_id, scope=scope, service=world.corte.public_id)
    return order


def _charge(world, method: str):
    plan = sales.Checkout.whole(method, received=D("25000") if method == "efectivo" else None)
    return sales.checkout_order(world.cashier, _order(world).public_id, scope=scope_of(world.cashier), checkout=plan)


def _manual(world, kind: str, session=None):
    return cash.register_manual_movement(
        world.cashier,
        (session or world.session).public_id,
        scope=scope_of(world.cashier),
        kind=kind,
        amount=D("1000"),
        payment_method="efectivo",
        description="Aseo",
    )


def _status(world) -> str:
    client = Client()
    client.force_login(world.cashier.user)
    return client.get(reverse("cash_register")).context["since"]


def test_el_estado_dice_desde_cuando_esta_abierta(world):
    assert _status(world).startswith("desde las ")
    _age(world, 1)
    assert _status(world).startswith("desde ayer, ")
    _age(world, 3)
    assert _status(world).startswith("desde el ")


@pytest.mark.parametrize("operation", ["cobro", "gasto", "retiro"])
def test_con_una_caja_de_ayer_no_se_mueve_efectivo(world, operation):
    _age(world, 1)
    with pytest.raises(ValidationError, match=STALE):
        if operation == "cobro":
            _charge(world, "efectivo")
        else:
            _manual(world, operation)


def test_con_una_caja_de_ayer_si_se_cobra_por_nequi(world):
    _age(world, 1)
    order, change = _charge(world, "nequi")
    assert (order.amount_paid, change) == (D("25000"), 0)


def test_al_cerrarla_y_abrir_la_de_hoy_todo_vuelve_a_funcionar(world):
    stale = _age(world, 1)
    cash.close_session(
        world.cashier, stale.public_id, scope=scope_of(world.cashier), counted_amount=expected_cash(stale)
    )
    today = cash.open_session(world.cashier, scope_of(world.cashier), opening_amount=D("50000"))

    _charge(world, "efectivo")
    _manual(world, "gasto", session=today)

    assert today.movements.count() == 2


def test_el_tablero_y_comandas_avisan_con_un_enlace_a_caja(world):
    _age(world, 1)
    client = Client()
    client.force_login(world.cashier.user)
    for url in (reverse("home"), reverse("orders_board")):
        html = client.get(url).content.decode()
        assert "viene de otro día" in html and reverse("cash_register") in html
