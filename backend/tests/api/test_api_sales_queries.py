"""Las listas de Comandas y Caja hacen las mismas consultas con pocas filas que con muchas."""

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.cash import services as cash
from tests.api.sales_support import cash_only, open_order, post
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db


def _queries(client, url_name: str, query: dict | None = None) -> int:
    client.get(reverse(url_name), query)  # la primera petición puede guardar la sede en la sesión
    with CaptureQueriesContext(connection) as context:
        assert client.get(reverse(url_name), query).status_code == 200
    return len(context.captured_queries)


def _sell(world, client, times: int) -> None:
    for _ in range(times):
        post(client, "api_order_checkout", cash_only("25000"), public_id=open_order(world).public_id)
        post(client, "api_cash_movement", {"kind": "gasto", "amount": "1000", "description": "Insumos"},
             session=world.session.public_id)  # fmt: skip


@pytest.mark.parametrize(
    ("url_name", "query"),
    [("api_orders", None), ("api_orders", {"estado": "cerradas"}), ("api_cash", None)],
)
def test_las_listas_no_crecen_en_consultas(world, cashier_client, url_name, query):
    _sell(world, cashier_client, 1)
    open_order(world)
    with_few = _queries(cashier_client, url_name, query)

    _sell(world, cashier_client, 4)
    for _ in range(3):
        open_order(world)

    assert _queries(cashier_client, url_name, query) == with_few


def test_el_historial_de_cierres_no_crece_en_consultas(world, cashier_client):
    scope = scope_of(world.cashier)
    cash.close_session(world.cashier, world.session.public_id, scope=scope, counted_amount=Decimal("50000"))
    with_one = _queries(cashier_client, "api_cash_closings")

    for _ in range(3):
        session = cash.open_session(world.cashier, scope, opening_amount=Decimal("0"))
        cash.close_session(world.cashier, session.public_id, scope=scope, counted_amount=Decimal("0"))

    assert _queries(cashier_client, "api_cash_closings") == with_one
