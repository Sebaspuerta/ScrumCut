"""Pantalla de Fiados (fase F4): abono en su sede, montos, pagar todo, caja de otro día, doble envío y cartera."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashSession
from apps.receivables import services as receivables
from apps.receivables.models import Receivable, ReceivablePayment, ReceivableStatus
from apps.sales.selectors import local_today
from apps.staff.models import BarberBranch
from apps.tenancy.models import Branch
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

D = Decimal


def _client(membership) -> Client:
    client = Client()
    client.force_login(membership.user)
    return client


def _notices(response) -> str:
    return " ".join(str(message) for message in get_messages(response.wsgi_request))


def _debt(world, total="30000", *, due_in=None, scope=None) -> Receivable:
    due = local_today(world.owner) + timedelta(days=due_in) if due_in is not None else None
    return receivables.create_manual(
        world.owner,
        world.laura.public_id,
        scope=scope or scope_of(world.owner, world.branch),
        total=D(total),
        due_date=due,
    )


def _pay(world, debt, **data):
    form = {"metodo": "efectivo", "saldo_visto": str(debt.balance), **data}
    return _client(world.cashier).post(reverse("receivables_pay", args=[debt.public_id]), form)


def test_un_abono_en_otra_sede_se_rechaza(world):
    norte = Branch.objects.create(name="Norte")
    BarberBranch.objects.create(barber=world.ana, branch=norte)
    cash.open_session(world.owner, scope_of(world.owner, norte), opening_amount=D("0"))
    in_norte = _debt(world, scope=scope_of(world.owner, norte))

    response = _pay(world, in_norte, monto="10000")

    assert response.status_code == 404
    assert not ReceivablePayment.objects.exists()


@pytest.mark.parametrize("amount", ["0", "40000"])
def test_un_monto_en_cero_o_mayor_que_el_saldo_se_rechaza(world, amount):
    debt = _debt(world)
    response = _pay(world, debt, monto=amount)
    debt.refresh_from_db()
    assert debt.balance == D("30000")
    assert _notices(response)


def test_pagar_todo_deja_el_saldo_en_cero_y_el_fiado_pagado(world):
    debt = _debt(world)
    _pay(world, debt, monto="10000")
    debt.refresh_from_db()

    _pay(world, debt, pagar_todo="1", metodo="nequi")

    debt.refresh_from_db()
    assert (debt.balance, debt.status) == (D("0"), ReceivableStatus.PAID)


def test_con_caja_de_otro_dia_el_efectivo_se_rechaza_y_nequi_pasa(world):
    debt = _debt(world)
    CashSession.objects.filter(pk=world.session.pk).update(opened_at=timezone.now() - timedelta(days=1))

    rejected = _pay(world, debt, monto="5000")
    assert "viene de otro día" in _notices(rejected)
    _pay(world, debt, monto="5000", metodo="nequi")

    debt.refresh_from_db()
    assert debt.balance == D("25000")


def test_el_doble_envio_no_abona_dos_veces(world):
    debt = _debt(world)
    first = _pay(world, debt, monto="10000")
    second = _pay(world, debt, monto="10000")  # el mismo formulario: vio un saldo de 30 000

    assert "registrado" in _notices(first)
    assert "cambió" in _notices(second)
    assert ReceivablePayment.objects.filter(receivable=debt).count() == 1


def _board(world, tab="pendientes"):
    return _client(world.cashier).get(reverse("receivables_board"), {"pestana": tab}).context


def test_los_tramos_de_antiguedad_suman_el_total_por_cobrar(world):
    for total, due_in in (("10000", 5), ("20000", -3), ("30000", -20), ("40000", -45), ("5000", None)):
        _debt(world, total, due_in=due_in)

    context = _board(world)

    amounts = {bucket["key"]: bucket["amount"] for bucket in context["aging"]}
    assert amounts == {"current": D("15000"), "d1_15": D("20000"), "d16_30": D("30000"), "d30": D("40000")}
    assert sum(amounts.values()) == context["data"]["pendientes_total"] == D("105000")


def test_la_lista_va_por_urgencia_los_mas_vencidos_primero(world):
    _debt(world, "1000", due_in=10)
    _debt(world, "2000", due_in=-30)
    _debt(world, "3000", due_in=None)
    _debt(world, "4000", due_in=-2)

    rows = _board(world)["rows"]

    assert [row["receivable"].total for row in rows] == [D("2000"), D("4000"), D("1000"), D("3000")]
    assert rows[0]["status"]["text"] == "▾ Vencido hace 30 días"


# Sesión, alcance, marco, la cartera en una consulta, lo cobrado en el mes y la página de fiados.
BOARD_QUERIES = 15


@pytest.mark.parametrize("debts", [1, 6])
def test_la_cartera_no_crece_con_el_numero_de_fiados(world, django_assert_num_queries, debts):
    for number in range(debts):
        _debt(world, "1000", due_in=number - 3)
    cashier = _client(world.cashier)
    with django_assert_num_queries(BOARD_QUERIES):
        cashier.get(reverse("receivables_board"))
