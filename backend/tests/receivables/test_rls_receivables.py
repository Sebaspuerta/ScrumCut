"""Barrera 2 para fiados: PostgreSQL aísla cuentas por cobrar y abonos con SQL directo."""

from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from apps.accounts.models import User
from apps.cash.models import CashMovement, CashSession
from apps.clients.models import Client
from apps.core.tenant_context import tenant_context
from apps.receivables.models import Receivable, ReceivablePayment
from apps.tenancy.models import Branch
from tests.rls_support import become_app_role, insert_as, insert_is_rejected, visible_barbershops

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

INSERTS = {
    "receivables_receivable": (
        "INSERT INTO receivables_receivable (public_id, created_at, updated_at, barbershop_id, client_id, total, "
        "balance, status, notes, created_by_id) VALUES (gen_random_uuid(), now(), now(), %s, %s, 1000, 1000, "
        "'pendiente', '', %s)",
        lambda shop, rows: [shop.pk, rows[shop.pk]["client"].pk, rows["user"].pk],
    ),
    # El movimiento libre evita chocar con el OneToOne del abono que ya existe.
    "receivables_receivablepayment": (
        "INSERT INTO receivables_receivablepayment (public_id, created_at, updated_at, barbershop_id, "
        "receivable_id, cash_movement_id, amount, method, received_by_id) VALUES (gen_random_uuid(), now(), now(), "
        "%s, %s, %s, 100, 'efectivo', %s)",
        lambda shop, rows: [
            shop.pk,
            rows[shop.pk]["receivable"].pk,
            rows[shop.pk]["spare_movement"].pk,
            rows["user"].pk,
        ],
    ),
}


def _movement(session, user) -> CashMovement:
    return CashMovement.objects.create(
        session=session,
        kind="abono_fiado",
        direction="in",
        amount=Decimal("100"),
        payment_method="efectivo",
        description="Abono",
        created_by=user,
    )


@pytest.fixture
def two_shops(make_shop):
    a, b = make_shop("a"), make_shop("b")
    rows = {"user": User.objects.create_user(email="rls@fiados.test")}
    user = rows["user"]
    for shop in (a, b):
        with tenant_context(shop.pk):
            client = Client.objects.create(
                full_name="Cliente", data_consent_at=timezone.now(), data_policy_version="2026-10"
            )
            receivable = Receivable.objects.create(
                client=client, total=Decimal("1000"), balance=Decimal("900"), created_by=user
            )
            session = CashSession.objects.create(
                branch=Branch.objects.create(name="Centro"), opened_by=user, opening_amount=Decimal("0")
            )
            ReceivablePayment.objects.create(
                receivable=receivable,
                cash_movement=_movement(session, user),
                amount=Decimal("100"),
                method="efectivo",
                received_by=user,
            )
            rows[shop.pk] = {"client": client, "receivable": receivable, "spare_movement": _movement(session, user)}
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
