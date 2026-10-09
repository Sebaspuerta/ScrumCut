"""Barrera 2 para caja: PostgreSQL aísla sesiones y movimientos con SQL directo."""

from decimal import Decimal

import pytest
from django.db import connection

from apps.accounts.models import User
from apps.cash.models import CashMovement, CashSession
from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Branch
from tests.rls_support import become_app_role, insert_as, insert_is_rejected, visible_barbershops

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

INSERTS = {
    # La sede libre evita chocar con la única caja abierta por sede.
    "cash_cashsession": (
        "INSERT INTO cash_cashsession (public_id, created_at, updated_at, barbershop_id, branch_id, opened_by_id, "
        "opened_at, opening_amount, notes) VALUES (gen_random_uuid(), now(), now(), %s, %s, %s, now(), 0, '')",
        lambda shop, rows: [shop.pk, rows[shop.pk]["free_branch"].pk, rows["user"].pk],
    ),
    "cash_cashmovement": (
        "INSERT INTO cash_cashmovement (public_id, created_at, updated_at, barbershop_id, session_id, kind, "
        "direction, amount, payment_method, description, created_by_id) "
        "VALUES (gen_random_uuid(), now(), now(), %s, %s, 'venta', 'in', 1000, 'efectivo', 'x', %s)",
        lambda shop, rows: [shop.pk, rows[shop.pk]["session"].pk, rows["user"].pk],
    ),
}


@pytest.fixture
def two_shops(make_shop):
    a, b = make_shop("a"), make_shop("b")
    rows = {"user": User.objects.create_user(email="rls@caja.test")}
    for shop in (a, b):
        with tenant_context(shop.pk):
            branch = Branch.objects.create(name="Centro")
            session = CashSession.objects.create(branch=branch, opened_by=rows["user"], opening_amount=Decimal("0"))
            CashMovement.objects.create(
                session=session,
                kind="venta",
                direction="in",
                amount=Decimal("1000"),
                payment_method="efectivo",
                description="Venta",
                created_by=rows["user"],
            )
            rows[shop.pk] = {"session": session, "free_branch": Branch.objects.create(name="Norte")}
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
