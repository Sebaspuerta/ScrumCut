"""Barrera 2 para comandas: PostgreSQL aísla órdenes, líneas y pagos con SQL directo."""

from decimal import Decimal

import pytest
from django.db import connection

from apps.accounts.models import User
from apps.cash.models import CashMovement, CashSession
from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context
from apps.sales.models import Order, OrderItem, Payment
from apps.tenancy.models import Branch
from tests.rls_support import become_app_role, insert_as, insert_is_rejected, visible_barbershops

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

INSERTS = {
    "sales_order": (
        "INSERT INTO sales_order (public_id, created_at, updated_at, barbershop_id, number, branch_id, status, "
        "payment_status, subtotal, discount, discount_reason, total, amount_paid, commission_total, created_by_id, "
        "cancel_reason) VALUES (gen_random_uuid(), now(), now(), %s, 100, %s, 'abierta', 'pendiente', 0, 0, '', "
        "0, 0, 0, %s, '')",
        lambda shop, rows: [shop.pk, rows[shop.pk]["branch"].pk, rows["user"].pk],
    ),
    "sales_orderitem": (
        "INSERT INTO sales_orderitem (public_id, created_at, updated_at, barbershop_id, order_id, item_type, "
        "service_id, quantity, name, unit_price, line_total, line_discount, unit_cost, consumables_cost, "
        "commission_type, commission_amount) VALUES (gen_random_uuid(), now(), now(), %s, %s, 'servicio', %s, 1, "
        "'Corte', 0, 0, 0, 0, 0, '', 0)",
        lambda shop, rows: [shop.pk, rows[shop.pk]["order"].pk, rows[shop.pk]["service"].pk],
    ),
    # El movimiento libre evita chocar con el OneToOne del pago que ya existe.
    "sales_payment": (
        "INSERT INTO sales_payment (public_id, created_at, updated_at, barbershop_id, order_id, cash_movement_id, "
        "method, amount, reference, received_by_id) VALUES (gen_random_uuid(), now(), now(), %s, %s, %s, "
        "'efectivo', 1000, '', %s)",
        lambda shop, rows: [shop.pk, rows[shop.pk]["order"].pk, rows[shop.pk]["spare_movement"].pk, rows["user"].pk],
    ),
}


def _movement(session, user) -> CashMovement:
    return CashMovement.objects.create(
        session=session,
        kind="venta",
        direction="in",
        amount=Decimal("1000"),
        payment_method="efectivo",
        description="Venta",
        created_by=user,
    )


@pytest.fixture
def two_shops(make_shop):
    a, b = make_shop("a"), make_shop("b")
    rows = {"user": User.objects.create_user(email="rls@ventas.test")}
    user = rows["user"]
    for shop in (a, b):
        with tenant_context(shop.pk):
            branch = Branch.objects.create(name="Centro")
            service = Service.objects.create(name="Corte", price=Decimal("1000"), duration_minutes=30)
            order = Order.objects.create(number=1, branch=branch, created_by=user)
            OrderItem.objects.create(
                order=order,
                item_type="servicio",
                service=service,
                quantity=1,
                name="Corte",
                unit_price=Decimal("1000"),
                line_total=Decimal("1000"),
            )
            session = CashSession.objects.create(branch=branch, opened_by=user, opening_amount=Decimal("0"))
            Payment.objects.create(
                order=order,
                cash_movement=_movement(session, user),
                method="efectivo",
                amount=Decimal("1000"),
                received_by=user,
            )
            rows[shop.pk] = {
                "branch": branch,
                "service": service,
                "order": order,
                "spare_movement": _movement(session, user),
            }
    return a, b, rows


@pytest.mark.parametrize("table", list(INSERTS))
def test_cada_barberia_ve_solo_sus_filas_y_no_inserta_en_otra(two_shops, table):
    a, b, rows = two_shops
    sql, params_for = INSERTS[table]
    become_app_role(table)

    seen_a, seen_b = visible_barbershops(table, a.pk), visible_barbershops(table, b.pk)
    assert seen_a and set(seen_a) == {a.pk}
    assert seen_b and set(seen_b) == {b.pk}
    assert visible_barbershops(table, None) == []

    insert_as(a.pk, sql, params_for(a, rows))  # control positivo
    assert len(visible_barbershops(table, a.pk)) == len(seen_a) + 1
    assert insert_is_rejected(a.pk, sql, params_for(b, rows))
