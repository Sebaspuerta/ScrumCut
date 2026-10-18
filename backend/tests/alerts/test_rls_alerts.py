"""Barrera 2 para alertas: PostgreSQL aísla `alerts_alert` con SQL directo."""

import pytest
from django.db import connection

from apps.alerts.models import Alert, AlertType
from apps.core.tenant_context import tenant_context
from apps.inventory.models import Product
from apps.tenancy.models import Branch
from tests.rls_support import become_app_role, insert_as, insert_is_rejected, visible_barbershops

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

TABLE = "alerts_alert"
# Tipo "stock_bajo" para no chocar con la alerta "agotado" abierta que ya tiene el producto.
INSERT_ALERT = (
    "INSERT INTO alerts_alert (public_id, created_at, updated_at, barbershop_id, alert_type, product_id, "
    "branch_id, message) VALUES (gen_random_uuid(), now(), now(), %s, 'stock_bajo', %s, %s, 'x')"
)


@pytest.fixture
def two_shops(make_shop):
    a, b = make_shop("a"), make_shop("b")
    rows = {}
    for shop in (a, b):
        with tenant_context(shop.pk):
            branch = Branch.objects.get()
            product = Product.objects.create(name="Cera", product_type="venta")
            Alert.objects.create(
                alert_type=AlertType.OUT_OF_STOCK, product=product, branch=branch, message="Cera agotada."
            )
            rows[shop.pk] = [product.pk, branch.pk]
    return a, b, rows


def test_cada_barberia_ve_solo_sus_alertas_y_no_inserta_en_otra(two_shops):
    a, b, rows = two_shops
    become_app_role(TABLE)

    assert visible_barbershops(TABLE, a.pk) == [a.pk]
    assert visible_barbershops(TABLE, b.pk) == [b.pk]
    assert visible_barbershops(TABLE, None) == []

    insert_as(a.pk, INSERT_ALERT, [a.pk, *rows[a.pk]])  # control positivo
    assert visible_barbershops(TABLE, a.pk) == [a.pk, a.pk]
    assert insert_is_rejected(a.pk, INSERT_ALERT, [b.pk, *rows[b.pk]])
