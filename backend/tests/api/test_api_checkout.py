"""Cobro en la API: una forma de pago, pago dividido (suma exacta, hasta 3 partes), fiado y un solo cobro
aunque lleguen dos a la vez."""

import threading

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse

from apps.cash.models import CashMovement, MovementKind
from apps.core.tenant_context import tenant_context
from apps.receivables.models import Receivable
from apps.sales.models import Order, OrderStatus, Payment, PaymentStatus
from tests.api.sales_support import cash_only, open_order, post
from tests.concurrency import run_threads

pytestmark = pytest.mark.django_db


def _checkout(client: Client, order: Order, body: dict):
    return post(client, "api_order_checkout", body, public_id=order.public_id)


def test_una_sola_forma_de_pago_devuelve_las_vueltas(world, cashier_client):
    order = open_order(world)

    response = _checkout(cashier_client, order, cash_only("30000"))

    assert response.status_code == 200
    assert response.json()["change"] == "5000.00"
    assert response.json()["order"]["status"] == OrderStatus.CLOSED


def test_con_efectivo_pide_lo_recibido_con_el_mensaje_de_django(world, cashier_client):
    response = _checkout(cashier_client, open_order(world), {"parts": [{"method": "efectivo"}]})

    assert response.status_code == 400
    assert response.json()["field_errors"] == {"received": ["Indica cuánto recibiste en efectivo."]}


def test_el_pago_dividido_debe_sumar_exactamente_el_total(world, cashier_client):
    order = open_order(world)
    parts = [{"method": "efectivo", "amount": "10000"}, {"method": "nequi", "amount": "14000"}]

    response = _checkout(cashier_client, order, {"parts": parts, "received": "10000"})

    assert response.status_code == 400
    assert response.json()["detail"] == "La suma de los pagos debe ser exactamente el total de la comanda ($25.000)."
    assert Order.objects.get(pk=order.pk).status == OrderStatus.OPEN


def test_el_pago_dividido_admite_hasta_tres_partes(world, cashier_client):
    order = open_order(world)
    four = [{"method": "nequi", "amount": amount} for amount in ("10000", "5000", "5000", "5000")]

    rejected = _checkout(cashier_client, order, {"parts": four})
    three = [
        {"method": "efectivo", "amount": "10000"},
        {"method": "nequi", "amount": "10000", "reference": "N-1"},
        {"method": "bre_b", "amount": "5000"},
    ]
    accepted = _checkout(cashier_client, order, {"parts": three, "received": "20000"})

    assert rejected.status_code == 400
    assert rejected.json()["field_errors"]["parts"] == ["El pago se divide en 3 partes como máximo."]
    assert accepted.status_code == 200
    assert accepted.json()["change"] == "10000.00"  # vueltas solo sobre la parte en efectivo
    assert sorted(Payment.objects.values_list("method", flat=True)) == ["bre_b", "efectivo", "nequi"]


def test_una_parte_a_fiado_deja_el_saldo_como_fiado_del_cliente(world, cashier_client):
    order = open_order(world, client=world.laura.public_id)
    parts = [{"method": "nequi", "amount": "15000"}, {"method": "fiado", "amount": "10000"}]

    response = _checkout(cashier_client, order, {"parts": parts, "due_date": "2026-12-01"})

    assert response.status_code == 200
    assert response.json()["order"]["balance"] == "10000.00"
    assert Order.objects.get(pk=order.pk).payment_status == PaymentStatus.CREDIT
    assert Receivable.objects.get().balance == 10000


def test_sin_cliente_no_hay_fiado(world, cashier_client):
    order = open_order(world)

    detail = cashier_client.get(reverse("api_order", kwargs={"public_id": order.public_id})).json()
    response = _checkout(cashier_client, order, {"parts": [{"method": "fiado"}]})

    assert detail["credit"] is None
    assert response.status_code == 400
    assert response.json()["detail"] == "Un fiado necesita un cliente."


def test_un_segundo_cobro_de_la_misma_comanda_no_cobra_dos_veces(world, cashier_client):
    order = open_order(world)

    first = _checkout(cashier_client, order, {"parts": [{"method": "nequi"}]})
    second = _checkout(cashier_client, order, {"parts": [{"method": "nequi"}]})

    assert first.status_code == 200
    assert (second.status_code, second.json()["code"]) == (400, "not_editable")
    assert Payment.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_dos_cobros_simultaneos_dan_un_solo_cobro(world):
    """Dos pestañas o dos cajeros: `close_order` bloquea la fila y el segundo encuentra la comanda cerrada."""
    order = open_order(world)
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def charge() -> None:
        try:
            client = Client()
            client.force_login(world.cashier.user)
            barrier.wait()
            statuses.append(_checkout(client, order, {"parts": [{"method": "nequi"}]}).status_code)
        finally:
            connection.close()

    run_threads([threading.Thread(target=charge, name=f"cobro-{number}") for number in range(2)])

    assert sorted(statuses) == [200, 400]
    with tenant_context(world.shop.pk):
        assert Payment.objects.count() == 1
        assert CashMovement.objects.filter(kind=MovementKind.SALE).count() == 1
