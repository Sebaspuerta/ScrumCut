"""Tablero ejecutivo: indicadores y variación y cuadre de caja. Las ventas por día: test_sales_calendar.py."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.selectors import expected_cash
from apps.core.formatting import format_variation
from apps.receivables import services as receivables
from apps.reports.selectors.dashboard import executive_dashboard
from apps.sales.selectors import local_today
from tests.conftest import scope_of
from tests.reports.helpers import BOGOTA, sell

pytestmark = pytest.mark.django_db

D = Decimal


def _dashboard(w, *, scope=None):
    return executive_dashboard(w.owner, local_today(w.owner), scope=scope or scope_of(w.owner, w.branch))


# Miércoles 14 de octubre de 2026; la semana anterior es el miércoles 7. Horas locales de Bogotá.
WEDNESDAY = date(2026, 10, 14)


def _at(day: date, hour: int):
    return mock.patch(
        "django.utils.timezone.now", return_value=datetime(day.year, day.month, day.day, hour, tzinfo=BOGOTA)
    )


def _sell_at(w, day: date, hour: int, **item):
    with _at(day, hour):
        sell(w, w.beto, **item)


def _kpis_at(w, hour: int) -> dict:
    with _at(WEDNESDAY, hour):
        return _dashboard(w)["kpis"]


def test_antes_de_la_primera_venta_no_hay_referencia(world):
    w = world
    _sell_at(w, WEDNESDAY - timedelta(days=7), 10, product=w.cera)  # después del corte de las 9 a. m.

    kpis = _kpis_at(w, 9)

    assert kpis["income"]["value"] == 0
    assert kpis["income"]["variation"] is None and kpis["orders"]["variation"] is None
    assert format_variation(kpis["income"]["variation"], "Sin referencia") == "Sin referencia"


def test_a_mitad_del_dia_se_compara_hasta_la_misma_hora_de_la_semana_anterior(world):
    w = world
    last_week = WEDNESDAY - timedelta(days=7)
    _sell_at(w, last_week, 10, product=w.cera)  # 20 000 antes del corte: cuenta
    _sell_at(w, last_week, 18, service=w.barba)  # 15 000 después del corte: no cuenta
    _sell_at(w, WEDNESDAY - timedelta(days=1), 11, service=w.corte)  # ayer: no es la referencia
    _sell_at(w, WEDNESDAY, 11, service=w.corte)  # hoy: 25 000

    kpis = _kpis_at(w, 15)

    assert kpis["comparison"] == "vs. miércoles anterior a esta hora"
    assert (kpis["income"]["value"], kpis["income"]["variation"]["percent"]) == (D("25000"), D("25.0"))
    assert (kpis["orders"]["value"], kpis["orders"]["variation"]["percent"]) == (1, D("0.0"))


def test_sin_ventas_de_referencia_dice_sin_referencia(world):
    w = world
    _sell_at(w, WEDNESDAY, 11, service=w.corte)

    kpis = _kpis_at(w, 15)

    assert kpis["income"]["value"] == D("25000")
    assert kpis["income"]["variation"] is None and kpis["orders"]["variation"] is None


def test_el_ticket_se_compara_con_el_periodo_anterior_del_mismo_largo(world):
    w = world
    _sell_at(w, WEDNESDAY - timedelta(days=1), 12, product=w.cera)  # dentro del mismo mes
    _sell_at(w, WEDNESDAY, 9, service=w.corte)
    _sell_at(w, WEDNESDAY, 10, service=w.barba)

    kpis = _kpis_at(w, 15)

    assert kpis["ticket"]["value"] == D("20000")  # 60 000 en 3 comandas
    assert kpis["ticket"]["variation"] is None  # el período anterior no vendió
    assert (kpis["cash"]["expected"], kpis["cash"]["opened_at"]) == (expected_cash(w.session), w.session.opened_at)


def test_fiados_pendientes_con_vencidos_y_clientes(world):
    w = world
    receivables.create_manual(
        w.cashier,
        w.laura.public_id,
        total=D("30000"),
        scope=scope_of(w.cashier, w.branch),
        due_date=timezone.localdate() - timedelta(1),
    )

    debts = _dashboard(w)["kpis"]["receivables"]

    assert (debts["pending_balance"], debts["overdue_count"], debts["clients"]) == (D("30000"), 1, 1)


def test_la_cascada_de_caja_cuadra_con_el_arqueo(world):
    w = world
    sell(w, w.ana, service=w.corte)  # +25 000 en efectivo
    sell(w, w.beto, service=w.barba, method="nequi")  # no entra a la caja
    for kind, amount in (("ingreso_manual", "1000"), ("gasto", "4000"), ("retiro", "9000")):
        cash.register_manual_movement(
            w.cashier,
            w.session.public_id,
            kind=kind,
            amount=D(amount),
            payment_method="efectivo",
            description="Prueba",
            scope=scope_of(w.cashier),
        )

    flow = _dashboard(w)["cash"]["flow"]
    steps = {step["label"]: step for step in flow["steps"]}
    entradas = sum(step["amount"] for step in flow["steps"] if step["kind"] == "up")
    salidas = sum(step["amount"] for step in flow["steps"] if step["kind"] == "down")

    assert list(steps) == [
        "Apertura",
        "Ventas en efectivo",
        "Abonos de fiados",
        "Otros ingresos",
        "Gastos",
        "Retiros",
        "Esperado",
    ]
    assert steps["Apertura"]["amount"] + entradas - salidas == steps["Esperado"]["amount"] == expected_cash(w.session)
    assert flow["is_open"] and "Contado" not in steps


def test_al_cerrar_la_caja_aparece_el_contado_y_la_diferencia(world):
    w = world
    sell(w, w.ana, service=w.corte)
    cash.close_session(
        w.cashier, w.session.public_id, counted_amount=D("74000"), scope=scope_of(w.cashier), notes="Faltó cambio"
    )

    flow = _dashboard(w)["cash"]["flow"]

    assert [step["label"] for step in flow["steps"]][-1] == "Contado"
    assert (flow["is_open"], flow["difference"]) == (False, D("-1000"))


def test_sin_caja_hoy_no_hay_cuadre(world):
    w = world
    cash.close_session(w.cashier, w.session.public_id, counted_amount=D("50000"), scope=scope_of(w.cashier))
    with mock.patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(days=1)):
        assert _dashboard(w)["cash"] == {"needs_branch": False, "flow": None}


def test_en_todas_las_sedes_no_se_mezclan_cajas(world):
    cash_today = _dashboard(world, scope=scope_of(world.owner, everything=True))["cash"]
    assert cash_today == {"needs_branch": True, "flow": None}
