"""Reporte de fiados: deuda viva por cliente, con lo vencido por fecha (regla 29)."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.receivables import services as receivables
from apps.reports.selectors.receivables import receivables_report
from apps.sales.selectors import local_today

pytestmark = pytest.mark.django_db

D = Decimal


def test_deuda_por_cliente_con_lo_vencido(world):
    w = world
    today = local_today(w.owner)
    receivables.create_manual(w.cashier, w.laura.public_id, D("30000"), due_date=today - timedelta(days=1))
    receivables.create_manual(w.cashier, w.laura.public_id, D("10000"), due_date=today + timedelta(days=5))
    paid = receivables.create_manual(w.cashier, w.laura.public_id, D("5000"))
    receivables.add_payment(w.cashier, paid.public_id, D("5000"), "efectivo", w.branch.public_id)

    report = receivables_report(w.owner)

    [laura] = report["by_client"]
    assert (laura["client__full_name"], laura["receivables"]) == ("Laura Gómez", 2)
    assert (laura["pending_balance"], laura["overdue_balance"]) == (D("40000"), D("30000"))
    assert (report["summary"]["pending_balance"], report["summary"]["overdue_count"]) == (D("40000"), 1)
