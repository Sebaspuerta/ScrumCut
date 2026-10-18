"""La base rechaza una sede, membresía o barbero de otra barbería en cada llave compuesta (docs/sedes.md).

Con el rol sin privilegios y la barbería A fijada, la fila es de A (RLS la deja pasar) pero
apunta a una sede de B. Una FK simple lo aceptaría, porque las llaves foráneas ignoran RLS:
el rechazo solo puede venir de la llave (barbershop_id, branch_id). El control positivo con
una sede propia descarta cualquier otra causa.
"""

from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Service
from apps.clients.models import Client
from apps.core.tenant_context import tenant_context
from apps.inventory.models import Product
from apps.staff.models import Barber
from apps.tenancy.models import Branch, Membership
from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD
from tests.rls_support import become_production_role, insert_as, insert_is_rejected, postgres_only

pytestmark = [pytest.mark.django_db, postgres_only]

ORDER = (
    "INSERT INTO sales_order (public_id, created_at, updated_at, barbershop_id, number, branch_id, status, "
    "payment_status, subtotal, discount, discount_reason, total, amount_paid, commission_total, created_by_id, "
    "cancel_reason) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(number)s, %(branch)s, 'abierta', "
    "'pendiente', 0, 0, '', 0, 0, 0, %(user)s, '')"
)
CASH_SESSION = (
    "INSERT INTO cash_cashsession (public_id, created_at, updated_at, barbershop_id, branch_id, opened_by_id, "
    "opened_at, opening_amount, notes) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(branch)s, %(user)s, "
    "now(), 0, '')"
)
RECEIVABLE = (
    "INSERT INTO receivables_receivable (public_id, created_at, updated_at, barbershop_id, client_id, "
    "origin_branch_id, total, balance, status, notes, created_by_id) VALUES (gen_random_uuid(), now(), now(), "
    "%(shop)s, %(client)s, %(branch)s, 1000, 1000, 'pendiente', '', %(user)s)"
)
CASHIER_ACCESS = (
    "INSERT INTO tenancy_membershipbranch (public_id, created_at, updated_at, barbershop_id, membership_id, "
    "branch_id) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(cashier)s, %(branch)s)"
)
BARBER_BRANCH = (
    "INSERT INTO staff_barberbranch (public_id, created_at, updated_at, barbershop_id, barber_id, branch_id) "
    "VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(barber)s, %(branch)s)"
)
BRANCH_HOURS = (
    "INSERT INTO tenancy_branchhours (public_id, created_at, updated_at, barbershop_id, branch_id, weekday, "
    "opens_at, closes_at, is_closed) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(branch)s, 0, "
    "'09:00', '18:00', false)"
)
LAST_BRANCH = "UPDATE tenancy_membership SET last_branch_id = %(branch)s WHERE id = %(cashier)s"
SERVICE_PRICE = (
    "INSERT INTO catalog_servicebranchprice (public_id, created_at, updated_at, barbershop_id, service_id, "
    "branch_id, price) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(service)s, %(branch)s, 1000)"
)
PRODUCT_PRICE = (
    "INSERT INTO inventory_productbranchprice (public_id, created_at, updated_at, barbershop_id, product_id, "
    "branch_id, price) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(product)s, %(branch)s, 1000)"
)
AUDIT_EVENT = (
    "INSERT INTO audit_auditlog (barbershop_id, branch_id, action, entity, entity_id, user_agent, created_at) "
    "VALUES (%(shop)s, %(branch)s, 'prueba', 'tenancy.Branch', '', '', now())"
)
STOCK_LEVEL = (
    "INSERT INTO inventory_stocklevel (public_id, created_at, updated_at, barbershop_id, product_id, branch_id, "
    "quantity) VALUES (gen_random_uuid(), now(), now(), %(shop)s, %(product)s, %(branch)s, 0)"
)
STOCK_MOVEMENT = (
    "INSERT INTO inventory_stockmovement (public_id, created_at, updated_at, barbershop_id, product_id, branch_id, "
    "movement_type, quantity, stock_before, stock_after, unit_cost, reason, reference, created_by_id) VALUES "
    "(gen_random_uuid(), now(), now(), %(shop)s, %(product)s, %(branch)s, 'entrada', 1, 0, 1, 0, 'x', '', %(user)s)"
)
ALERT = (
    "INSERT INTO alerts_alert (public_id, created_at, updated_at, barbershop_id, alert_type, product_id, branch_id, "
    "message) VALUES (gen_random_uuid(), now(), now(), %(shop)s, 'agotado', %(product)s, %(branch)s, 'x')"
)

# (sentencia, dato que se toma de la otra barbería): sedes, y también membresías y barberos.
CASES = {
    "sales_order.branch": (ORDER, "branch"),
    "cash_cashsession.branch": (CASH_SESSION, "branch"),
    "receivables_receivable.origin_branch": (RECEIVABLE, "branch"),
    "tenancy_membershipbranch.branch": (CASHIER_ACCESS, "branch"),
    "tenancy_membershipbranch.membership": (CASHIER_ACCESS, "cashier"),
    "staff_barberbranch.branch": (BARBER_BRANCH, "branch"),
    "staff_barberbranch.barber": (BARBER_BRANCH, "barber"),
    "tenancy_branchhours.branch": (BRANCH_HOURS, "branch"),
    "tenancy_membership.last_branch": (LAST_BRANCH, "branch"),
    "audit_auditlog.branch": (AUDIT_EVENT, "branch"),
    "catalog_servicebranchprice.branch": (SERVICE_PRICE, "branch"),
    "catalog_servicebranchprice.service": (SERVICE_PRICE, "service"),
    "inventory_productbranchprice.branch": (PRODUCT_PRICE, "branch"),
    "inventory_productbranchprice.product": (PRODUCT_PRICE, "product"),
    "inventory_stocklevel.branch": (STOCK_LEVEL, "branch"),
    "inventory_stocklevel.product": (STOCK_LEVEL, "product"),
    "inventory_stockmovement.branch": (STOCK_MOVEMENT, "branch"),
    "alerts_alert.branch": (ALERT, "branch"),
}


def _rows_of(shop) -> dict:
    """Todo lo que cada sentencia necesita, con una sede propia libre (sin caja, horario ni accesos)."""
    with tenant_context(shop.pk):
        user = User.objects.create_user(email=f"cajero@{shop.slug}.test", password=TEST_PASSWORD)
        cashier = Membership.objects.create(user=user, barbershop=shop, role=Role.CASHIER)
        client = Client.objects.create(
            full_name="Laura",
            data_consent_at=timezone.now() - timedelta(days=1),
            data_policy_version="2026-10",
        )
        return {
            "shop": shop.pk,
            "user": user.pk,
            "cashier": cashier.pk,
            "client": client.pk,
            "barber": Barber.objects.create(display_name="Ana").pk,
            "service": Service.objects.create(name="Corte", price=1000, duration_minutes=30).pk,
            "product": Product.objects.create(name="Cera", product_type="venta").pk,
            "branch": Branch.objects.create(name="Libre").pk,
            "number": 900,
        }


@pytest.fixture
def two_shops(make_shop):
    a, b = make_shop("a"), make_shop("b")
    return _rows_of(a), _rows_of(b)


@pytest.mark.parametrize("case", list(CASES))
def test_la_base_rechaza_lo_que_apunta_a_otra_barberia(two_shops, case):
    rows_a, rows_b = two_shops
    sql, foreign = CASES[case]
    become_production_role()
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")  # las llaves son diferidas, como las de Django

    assert insert_is_rejected(rows_a["shop"], sql, {**rows_a, foreign: rows_b[foreign]})
    insert_as(rows_a["shop"], sql, rows_a)  # control positivo: con lo suyo sí pasa
