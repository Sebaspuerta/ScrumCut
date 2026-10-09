"""Tablero del día (regla 53, defecto 23) y "mis cortes de hoy" del barbero (regla 54)."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashSession
from apps.inventory import services as inventory
from apps.reports.selectors.dashboard import dashboard_summary
from apps.sales import selectors as sales_selectors
from apps.sales import services as sales
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

D = Decimal


def test_el_esperado_del_tablero_coincide_con_el_arqueo_de_una_caja_abierta_ayer(world):
    w = world
    yesterday = timezone.now() - timedelta(days=1)
    with mock.patch("django.utils.timezone.now", return_value=yesterday):
        sell(w, w.ana, service=w.corte)  # 25 000 en efectivo, ayer
    CashSession.objects.filter(pk=w.session.pk).update(opened_at=yesterday - timedelta(hours=2))
    sell(w, w.beto, product=w.cera)  # 20 000 en efectivo, hoy
    sales.create_order(w.cashier, w.branch.public_id)  # una comanda abierta

    summary = dashboard_summary(w.owner)
    closed = cash.close_session(w.cashier, w.session.public_id, D("95000"))

    assert [session["expected_cash"] for session in summary["open_cash_sessions"]] == [D("95000")]
    assert closed.expected_amount == D("95000")
    assert summary["income"]["total"] == D("20000")  # lo de ayer no es ingreso de hoy
    assert (summary["orders_closed_today"], summary["orders_open"]) == (1, 1)


def test_el_tablero_resta_las_devoluciones_y_suma_los_abonos(world):
    w = world
    returned = sell(w, w.ana, service=w.corte, method="nequi")
    sales.cancel_order(w.owner, returned.public_id, "Cobro duplicado")
    sell(w, w.beto, service=w.barba)

    income = dashboard_summary(w.owner)["income"]

    assert (income["sales"], income["refunds"], income["receivable_payments"], income["total"]) == (
        D("40000"),
        D("25000"),
        D("0"),
        D("15000"),
    )


def test_el_tablero_no_escribe_nada(world):
    sell(world, world.ana, service=world.corte)
    with CaptureQueriesContext(connection) as queries:
        summary = dashboard_summary(world.owner)
    writes = [q["sql"] for q in queries.captured_queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE"))]
    assert writes == []
    assert (summary["critical_stock"], summary["unread_alerts"]) == (0, 0)
    assert summary["receivables"]["pending_count"] == 0


def test_inventario_critico_usa_el_criterio_de_las_alertas(world):
    w = world

    def product(name, stock, **data):
        return inventory.create_product(w.owner, {"name": name, "product_type": "venta", **data}, initial_stock=stock)

    product("Talco", 0)  # agotado sin mínimo: cuenta
    product("Gel", 2, minimum_stock=3)  # bajo su mínimo: cuenta
    product("Aceite", 3, minimum_stock=3)  # en su mínimo: cuenta
    product("Loción", 4, minimum_stock=3)
    inventory.deactivate_product(w.owner, product("Pausado", 0).public_id)

    assert dashboard_summary(w.owner)["critical_stock"] == 3


def test_mis_cortes_de_hoy_solo_cuenta_lo_del_barbero_y_sin_dinero(world):
    w = world
    sell(w, w.ana, service=w.corte)
    sell(w, w.ana, service=w.corte, quantity=2)
    sell(w, w.beto, service=w.barba)

    assert sales_selectors.my_cuts_today(w.ana_login) == {"cuts_today": 3}
    assert sales_selectors.my_cuts_today(w.beto_login) == {"cuts_today": 1}
    with pytest.raises(PermissionDenied):
        dashboard_summary(w.ana_login)
