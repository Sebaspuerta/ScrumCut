"""Caja en la API: abrir, movimientos, la caja de otro día y el cierre con su conteo y nota."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashSession
from apps.cash.services import NOTE_REQUIRED, STALE_SESSION
from apps.tenancy.branch_scope import WRITE_NEEDS_ONE_BRANCH
from tests.api.sales_support import cash_only, open_order, post
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

EXPENSE = {"kind": "gasto", "amount": "8000", "description": "Café"}


def _close(client: Client, session: CashSession, bills: dict[int, int], notes: str = ""):
    body = {"bills": [{"denomination": bill, "count": count} for bill, count in bills.items()], "coins": "0"}
    return post(client, "api_cash_close", {**body, "notes": notes}, session=session.public_id)


def test_la_caja_trae_la_franja_los_movimientos_y_las_acciones(world, cashier_client):
    post(cashier_client, "api_order_checkout", cash_only("25000"), public_id=open_order(world).public_id)
    post(cashier_client, "api_cash_movement", EXPENSE, session=world.session.public_id)

    state = cashier_client.get(reverse("api_cash")).json()

    session = state["session"]
    assert session["strip"]["sales"] == {"total": "25000.00", "count": 1}
    assert session["expected"] == "67000.00"  # 50 000 + 25 000 − 8 000
    assert [(row["kind"], row["direction"]) for row in session["movements"]] == [("gasto", "out"), ("venta", "in")]
    assert state["actions"] == {"open": False, "movement": True, "close": True}
    assert state["denominations"][0] == 100000


def test_abrir_y_registrar_un_ingreso(world, cashier_client):
    cash.close_session(
        world.cashier, world.session.public_id, scope=scope_of(world.cashier), counted_amount=Decimal("50000")
    )

    opened = post(cashier_client, "api_cash_open", {"opening_amount": "30000"})
    session = opened.json()["session"]
    income = post(cashier_client, "api_cash_movement", {**EXPENSE, "kind": "ingreso_manual"}, session=session["id"])

    assert opened.status_code == 201
    assert income.json()["session"]["expected"] == "38000.00"


def test_en_todas_no_se_abre_caja(world, norte, owner_client):
    post(owner_client, "api_branch", {"sede": "todas"})

    state = owner_client.get(reverse("api_cash")).json()
    response = post(owner_client, "api_cash_open", {"opening_amount": "0"})

    assert (state["needs_branch"], state["session"]) == (True, None)
    assert response.json()["detail"] == WRITE_NEEDS_ONE_BRANCH


def test_la_caja_de_otro_dia_rechaza_los_movimientos_y_solo_se_cierra(world, cashier_client):
    CashSession.objects.filter(pk=world.session.pk).update(opened_at=timezone.now() - timedelta(days=1))

    state = cashier_client.get(reverse("api_cash")).json()
    movement = post(cashier_client, "api_cash_movement", EXPENSE, session=world.session.public_id)
    sale = post(cashier_client, "api_order_checkout", cash_only("25000"), public_id=open_order(world).public_id)

    assert state["session"]["stale"] is True
    assert state["actions"] == {"open": False, "movement": False, "close": True}
    assert (movement.status_code, movement.json()["code"], movement.json()["detail"]) == (
        400,
        "stale_session",
        STALE_SESSION,
    )
    assert sale.json()["code"] == "stale_session"
    assert _close(cashier_client, world.session, {50000: 1}).status_code == 200


def test_el_cierre_con_diferencia_exige_la_nota(world, cashier_client):
    without_note = _close(cashier_client, world.session, {20000: 2})
    with_note = _close(cashier_client, world.session, {20000: 2}, notes="Faltante en vueltas")

    assert without_note.status_code == 400
    assert without_note.json()["field_errors"] == {"notes": [NOTE_REQUIRED]}
    assert with_note.status_code == 200
    assert (with_note.json()["counted"], with_note.json()["difference"]) == ("40000.00", "-10000.00")


def test_el_contado_lo_suma_el_servidor_y_no_acepta_otra_denominacion(world, cashier_client):
    closed = _close(cashier_client, world.session, {20000: 2, 10000: 1})
    other = _close(cashier_client, world.session, {3000: 1})

    assert (closed.json()["counted"], closed.json()["difference"]) == ("50000.00", "0.00")
    assert other.status_code == 400


def test_el_historial_de_cierres_es_por_paginas(world, cashier_client):
    _close(cashier_client, world.session, {50000: 1})

    history = cashier_client.get(reverse("api_cash_closings")).json()

    assert (history["count"], history["pages"]) == (1, 1)
    assert history["results"][0]["closed_by"] == world.cashier.user.email


def test_el_barbero_no_ve_la_caja(world):
    ana = Client()
    ana.force_login(world.ana_login.user)

    assert ana.get(reverse("api_cash")).status_code == 403
