"""Escenario de un día completo, con las cifras a la vista.

Comanda: Corte (Ana, gasta 1 cuchilla) 25 000 + Barba (Beto) 15 000 + Cera 20 000.
Subtotal 60 000; descuento 5 000 "Cliente frecuente"; total 55 000.

Reparto del descuento (decisión 3), proporcional y con el residuo a la línea mayor:
  Corte 5000·25/60 = 2083,33 (+0,01 de residuo) = 2083,34
  Barba 5000·15/60 = 1250,00
  Cera  5000·20/60 = 1666,66                      suma 5000,00
Comisiones: Ana 40 % × (25 000 − 2 083,34) = 9 166,66; Beto 50 % × 13 750 = 6 875,00;
la Cera no comisiona. Total 16 041,66.
Pago mixto: 30 000 en efectivo + 25 000 por Nequi. Caja: base 50 000 + 30 000 = 80 000.
"""

from decimal import Decimal

import pytest

from apps.cash import selectors as cash_selectors
from apps.cash import services as cash
from apps.inventory.models import MovementType, StockMovement
from apps.sales import selectors, services
from apps.sales.models import ItemType, OrderStatus, PaymentStatus
from apps.staff import services as staff

pytestmark = pytest.mark.django_db

D = Decimal


def test_un_dia_de_barberia(world):
    w = world
    order = services.create_order(w.cashier, w.branch.public_id, client=w.laura.public_id, barber=w.ana.public_id)
    services.add_item(w.cashier, order.public_id, service=w.corte.public_id)
    services.add_item(w.cashier, order.public_id, service=w.barba.public_id, barber=w.beto.public_id)
    services.add_item(w.cashier, order.public_id, product=w.cera.public_id)
    services.set_discount(w.cashier, order.public_id, D("5000"), "Cliente frecuente")

    closed = services.close_order(
        w.cashier,
        order.public_id,
        [{"method": "efectivo", "amount": "30000"}, {"method": "nequi", "amount": "25000", "reference": "NQ-123"}],
    )

    # Comanda
    assert (closed.status, closed.payment_status) == (OrderStatus.CLOSED, PaymentStatus.PAID)
    assert (closed.subtotal, closed.discount, closed.total, closed.amount_paid) == (
        D("60000"),
        D("5000"),
        D("55000"),
        D("55000"),
    )
    assert closed.commission_total == D("16041.66")

    # Líneas: descuento repartido y comisiones copiadas
    lines = {line.name: line for line in closed.items.all()}
    assert lines["Corte"].line_discount == D("2083.34")
    assert lines["Barba"].line_discount == D("1250.00")
    assert lines["Cera"].line_discount == D("1666.66")
    assert sum(line.line_discount for line in lines.values()) == D("5000")
    assert (lines["Corte"].barber, lines["Corte"].commission_rate, lines["Corte"].commission_amount) == (
        w.ana,
        D("40"),
        D("9166.66"),
    )
    assert (lines["Barba"].barber, lines["Barba"].commission_amount) == (w.beto, D("6875.00"))
    assert (lines["Cera"].item_type, lines["Cera"].commission_amount, lines["Cera"].unit_cost) == (
        ItemType.PRODUCT,
        D("0"),
        D("8000"),
    )
    assert lines["Corte"].consumables_cost == D("1000")

    # Inventario: la cera vendida y la cuchilla gastada por el corte
    w.cera.refresh_from_db()
    w.cuchilla.refresh_from_db()
    assert (w.cera.current_stock, w.cuchilla.current_stock) == (4, 9)
    reference = f"order:{order.public_id}"
    assert set(StockMovement.objects.filter(reference=reference).values_list("movement_type", flat=True)) == {
        MovementType.SALE,
        MovementType.SERVICE,
    }

    # Caja y arqueo: solo el efectivo cuenta
    summary = cash_selectors.session_summary(w.cashier, w.session.public_id)
    assert summary["expected_cash"] == D("80000")
    assert summary["by_method"]["nequi"]["in"] == D("25000")
    assert summary["by_kind"]["venta"] == D("55000")
    session = cash.close_session(w.cashier, w.session.public_id, D("80000"))
    assert (session.expected_amount, session.difference) == (D("80000"), D("0"))

    # Cambiar la comisión de Ana después no reescribe el día (defecto 1)
    before = selectors.barber_performance(w.owner, w.ana.public_id)
    staff.set_commission(w.owner, w.ana.public_id, "percentage", D("60"))
    after = selectors.barber_performance(w.owner, w.ana.public_id)
    assert before["commission_total"] == after["commission_total"] == D("9166.66")
    assert after["sales_total"] == D("22916.66")
    assert (after["services_count"], after["orders_count"]) == (1, 1)
    assert selectors.my_cuts_today(w.ana_login) == {"cuts_today": 1}
