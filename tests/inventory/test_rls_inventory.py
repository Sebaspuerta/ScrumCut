"""Barrera 2 para inventario: PostgreSQL aísla las cuatro tablas con SQL directo."""

from decimal import Decimal

import pytest
from django.db import connection

from apps.accounts.models import User
from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context
from apps.inventory.models import Product, ProductCategory, ServiceConsumable, StockMovement
from tests.rls_support import become_app_role, insert_as, insert_is_rejected, visible_barbershops

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

INSERTS = {
    "inventory_productcategory": (
        "INSERT INTO inventory_productcategory (public_id, created_at, updated_at, barbershop_id, name) "
        "VALUES (gen_random_uuid(), now(), now(), %s, %s)",
        lambda shop, rows: [shop.pk, f"Nueva {shop.slug}"],
    ),
    "inventory_product": (
        "INSERT INTO inventory_product (public_id, created_at, updated_at, barbershop_id, name, product_type, "
        "purchase_cost, sale_price, current_stock, supplier, photo, is_active) "
        "VALUES (gen_random_uuid(), now(), now(), %s, %s, 'venta', 0, 0, 0, '', '', true)",
        lambda shop, rows: [shop.pk, f"Nuevo {shop.slug}"],
    ),
    "inventory_stockmovement": (
        "INSERT INTO inventory_stockmovement (public_id, created_at, updated_at, barbershop_id, product_id, "
        "movement_type, quantity, stock_before, stock_after, unit_cost, reason, created_by_id) "
        "VALUES (gen_random_uuid(), now(), now(), %s, %s, 'entrada', 1, 0, 1, 0, 'x', %s)",
        lambda shop, rows: [shop.pk, rows[shop.pk]["product"].pk, rows["user"].pk],
    ),
    "inventory_serviceconsumable": (
        "INSERT INTO inventory_serviceconsumable (public_id, created_at, updated_at, barbershop_id, service_id, "
        "product_id, quantity) VALUES (gen_random_uuid(), now(), now(), %s, %s, %s, 1)",
        lambda shop, rows: [shop.pk, rows[shop.pk]["service"].pk, rows[shop.pk]["spare_product"].pk],
    ),
}


@pytest.fixture
def two_shops(make_shop):
    a, b = make_shop("a"), make_shop("b")
    rows = {"user": User.objects.create_user(email="rls@inventario.test")}
    for shop in (a, b):
        with tenant_context(shop.pk):
            product = Product.objects.create(name=f"Cera {shop.slug}", product_type="venta")
            service = Service.objects.create(name=f"Corte {shop.slug}", price=Decimal("1"), duration_minutes=30)
            ProductCategory.objects.create(name=f"Cuidado {shop.slug}")
            StockMovement.objects.create(
                product=product,
                movement_type="entrada",
                quantity=1,
                stock_before=0,
                stock_after=1,
                unit_cost=Decimal("0"),
                reason="Inicial",
                created_by=rows["user"],
            )
            ServiceConsumable.objects.create(service=service, product=product, quantity=1)
            spare = Product.objects.create(name=f"Repuesto {shop.slug}", product_type="consumible")
            rows[shop.pk] = {"product": product, "service": service, "spare_product": spare}
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
