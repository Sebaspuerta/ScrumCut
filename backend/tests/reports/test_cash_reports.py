"""Cierres y movimientos de caja: lo guardado al cerrar, no un recálculo (defectos 18 a 20)."""

from decimal import Decimal

import pytest

from apps.cash import services as cash
from apps.reports.selectors.cash import cash_closings, cash_movements
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

D = Decimal


def test_cierres_con_esperado_contado_y_diferencia_guardados(world):
    w = world
    sell(w, w.ana, service=w.corte)  # efectivo
    sell(w, w.beto, service=w.barba, method="nequi")  # no entra al esperado
    cash.register_manual_movement(w.cashier, w.session.public_id, "gasto", D("5000"), "efectivo", "Aseo")
    cash.close_session(w.cashier, w.session.public_id, D("69000"))

    [closing] = cash_closings(w.owner)

    assert (closing["branch__name"], closing["opening_amount"]) == ("Centro", D("50000"))
    assert (closing["expected_amount"], closing["counted_amount"], closing["difference"]) == (
        D("70000"),
        D("69000"),
        D("-1000"),
    )


def test_movimientos_de_caja_del_periodo(world):
    w = world
    sell(w, w.ana, service=w.corte)
    cash.register_manual_movement(w.cashier, w.session.public_id, "gasto", D("5000"), "efectivo", "Aseo")

    rows = [(row["kind"], row["direction"], row["amount"]) for row in cash_movements(w.owner)]

    assert rows == [("venta", "in", D("25000")), ("gasto", "out", D("5000"))]
