"""Clientes y Fiados hacen las mismas consultas con pocos clientes, visitas y abonos que con muchos."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tests.api.sales_support import credit, new_client, post, sell

pytestmark = pytest.mark.django_db


def _queries(client, url: str, query: dict | None = None) -> int:
    client.get(url, query)  # la primera petición puede guardar la sede en la sesión
    with CaptureQueriesContext(connection) as context:
        assert client.get(url, query).status_code == 200
    return len(context.captured_queries)


def _grow(world, client, number: int) -> None:
    """Un cliente más con una visita y un fiado con un abono, y otra visita de Laura con su fiado."""
    customer = new_client(world, f"Cliente {number}", phone=f"31000000{number:02d}")
    sell(world, client, customer=customer)
    sell(world, client, customer=world.laura)
    for debtor in (customer, world.laura):
        debt = credit(world, debtor, total="20000")
        body = {"amount": "5000", "method": "efectivo", "expected_balance": "20000.00"}
        post(client, "api_receivable_pay", body, public_id=debt.public_id)


@pytest.mark.parametrize(
    ("url_name", "query"),
    [
        ("api_clients", None),
        ("api_clients", {"q": "cliente", "orden": "deuda"}),
        ("api_receivables", None),
        ("api_receivables", {"pestana": "pagados"}),
    ],
)
def test_las_listas_no_crecen_en_consultas(world, cashier_client, url_name, query):
    _grow(world, cashier_client, 1)
    with_few = _queries(cashier_client, reverse(url_name), query)

    for number in range(2, 6):
        _grow(world, cashier_client, number)

    assert _queries(cashier_client, reverse(url_name), query) == with_few


def test_la_ficha_del_cliente_no_crece_en_consultas(world, cashier_client):
    url = reverse("api_client", kwargs={"public_id": world.laura.public_id})
    _grow(world, cashier_client, 1)
    with_few = _queries(cashier_client, url)

    for number in range(2, 6):
        _grow(world, cashier_client, number)

    assert _queries(cashier_client, url) == with_few


def test_el_detalle_del_fiado_no_crece_en_consultas(world, cashier_client):
    debt = credit(world, world.laura, total="50000")
    url = reverse("api_receivable", kwargs={"public_id": debt.public_id})
    balance = 50000

    def pay() -> None:
        nonlocal balance
        body = {"amount": "1000", "method": "efectivo", "expected_balance": f"{balance}.00"}
        assert post(cashier_client, "api_receivable_pay", body, public_id=debt.public_id).status_code == 200
        balance -= 1000

    pay()
    with_one = _queries(cashier_client, url)
    for _ in range(4):
        pay()

    assert _queries(cashier_client, url) == with_one
