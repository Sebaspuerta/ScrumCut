"""El inventario hace las mismas consultas con pocos productos, sedes y movimientos que con muchos."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.inventory import services
from apps.sales.selectors import local_today
from tests.api.inventory_support import entry
from tests.api.sales_support import choose_branch, post
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db


def _queries(client, url: str) -> int:
    client.get(url)  # la primera petición puede guardar la sede en la sesión
    with CaptureQueriesContext(connection) as context:
        assert client.get(url).status_code == 200
    return len(context.captured_queries)


def _grow(world, norte, number: int) -> None:
    """Un perecedero más con stock bajo en las dos sedes, que vence pronto, con su precio en Norte."""
    data = {
        "name": f"Producto {number}",
        "product_type": "perecedero",
        "purchase_cost": Decimal("1000"),
        "sale_price": Decimal("2000"),
        "minimum_stock": 5,
        "expiration_date": local_today(world.owner) + timedelta(days=5),
    }
    product = services.create_product(world.owner, data, scope=scope_of(world.owner, world.branch), initial_stock=2)
    norte_scope = scope_of(world.owner, norte)
    services.register_entry(world.owner, product.public_id, scope=norte_scope, quantity=1, reason="Compra")
    services.set_product_branch_price(world.owner, product.public_id, scope=norte_scope, price=Decimal("3000"))


@pytest.mark.parametrize("branch_mode", ["una", "todas"])
@pytest.mark.parametrize("url_name", ["api_products", "api_inventory_alerts"])
def test_la_lista_y_los_avisos_no_crecen_en_consultas(world, norte, owner_client, url_name, branch_mode):
    if branch_mode == "todas":
        assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200
    else:
        choose_branch(owner_client, norte)
    _grow(world, norte, 1)
    with_few = _queries(owner_client, reverse(url_name))

    for number in range(2, 6):
        _grow(world, norte, number)

    assert _queries(owner_client, reverse(url_name)) == with_few


def test_el_detalle_no_crece_en_consultas(world, norte, owner_client):
    choose_branch(owner_client, world.branch)
    url = reverse("api_product", kwargs={"public_id": world.cera.public_id})
    entry(owner_client, world.cera)
    with_one = _queries(owner_client, url)

    for _ in range(4):
        entry(owner_client, world.cera)

    assert _queries(owner_client, url) == with_one
