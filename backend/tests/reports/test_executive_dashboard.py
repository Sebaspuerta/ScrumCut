"""Tablero ejecutivo: indicadores y variación, torres por semana y cuadre de caja."""

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
from tests.conftest import scope_of
from tests.reports.helpers import BOGOTA, close_at, sell

pytestmark = pytest.mark.django_db

D = Decimal


def _dashboard(w, date_from=None, date_to=None):
    return executive_dashboard(w.owner, date_from, date_to, scope=scope_of(w.owner, w.branch))


def _sell_on(w, days_ago, **item):
    with mock.patch("django.utils.timezone.now", return_value=timezone.now() - timedelta(days=days_ago)):
        sell(w, w.beto, **item)


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
    _sell_on(w, 1, product=w.cera)  # dentro de los últimos 30 días
    sell(w, w.ana, service=w.corte)
    sell(w, w.beto, service=w.barba)

    kpis = _dashboard(w)["kpis"]

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


def test_torres_por_semana_con_dias_sin_ventas_y_la_venta_de_las_11_pm(world):
    w = world
    close_at(sell(w, w.ana, service=w.corte), datetime(2026, 10, 5, 23, 0))  # lunes, 11 p. m. en Bogotá
    close_at(sell(w, w.beto, service=w.barba), datetime(2026, 10, 7, 12, 0))

    towers = _dashboard(w, date(2026, 10, 5), date(2026, 10, 7))["towers"]

    [week] = towers["weeks"]  # del lunes 5 al domingo 11
    by_day = {cell["date"]: cell for cell in week}
    assert by_day["2026-10-05"]["amount"] == "$25.000"
    assert (by_day["2026-10-06"]["amount"], by_day["2026-10-06"]["closed"]) == ("$0", True)
    assert not by_day["2026-10-08"]["in_period"]  # fuera del período: sin torre
    assert (towers["total"], towers["selling_days"], towers["best"]["day"]) == (D("40000"), 2, date(2026, 10, 5))
    assert [day["average"] for day in towers["weekdays"]][:3] == [D("25000"), None, D("15000")]


def test_la_cascada_de_caja_cuadra_con_el_arqueo(world):
    w = world
    sell(w, w.ana, service=w.corte)  # +25 000 en efectivo
    sell(w, w.beto, service=w.barba, method="nequi")  # no entra a la caja
    for kind, amount in (("ingreso_manual", "1000"), ("gasto", "4000"), ("retiro", "9000")):
        cash.register_manual_movement(
            w.cashier, w.session.public_id, kind=kind, amount=D(amount), payment_method="efectivo", description="Prueba"
        )

    flow = _dashboard(w)["cash_flow"]
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
    cash.close_session(w.cashier, w.session.public_id, counted_amount=D("74000"))

    flow = _dashboard(w)["cash_flow"]

    assert [step["label"] for step in flow["steps"]][-1] == "Contado"
    assert (flow["is_open"], flow["difference"]) == (False, D("-1000"))


def test_sin_caja_hoy_no_hay_cuadre(world):
    w = world
    cash.close_session(w.cashier, w.session.public_id, counted_amount=D("50000"))
    with mock.patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(days=1)):
        assert executive_dashboard(w.owner, None, None, scope=scope_of(w.owner, w.branch))["cash_flow"] is None
