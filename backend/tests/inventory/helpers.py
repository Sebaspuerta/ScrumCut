"""Datos de prueba de inventario, creados con los services reales."""

from decimal import Decimal

from apps.inventory import services
from apps.inventory.models import Product
from tests.conftest import scope_of


def make_product(actor, name="Cera mate", initial_stock=0, **data) -> Product:
    values = {
        "name": name,
        "product_type": "venta",
        "purchase_cost": Decimal("8000"),
        "sale_price": Decimal("15000"),
        **data,
    }
    return services.create_product(actor, values, initial_stock=initial_stock, scope=scope_of(actor))
