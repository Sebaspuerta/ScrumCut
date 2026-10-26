"""Apoyo de las pruebas de Comandas y Caja en la API: comandas abiertas con los services y peticiones JSON."""

from django.test import Client
from django.urls import reverse

from apps.sales import services
from apps.sales.models import Order
from apps.tenancy.models import Branch, Membership
from tests.conftest import scope_of


def open_order(world, *, actor: Membership | None = None, branch: Branch | None = None, client=None) -> Order:
    """Una comanda abierta con un corte de Ana, creada con los services como en la pantalla de Django."""
    actor = actor or world.cashier
    scope = scope_of(actor, branch or world.branch)
    order = services.create_order(actor, scope, client=client, barber=world.ana.public_id)
    services.add_item(actor, order.public_id, scope=scope, service=world.corte.public_id)
    order.refresh_from_db()
    return order


def post(client: Client, name: str, body: dict | None = None, **kwargs):
    return client.post(reverse(name, kwargs=kwargs or None), body or {}, content_type="application/json")


def choose_branch(client: Client, branch: Branch) -> None:
    assert post(client, "api_branch", {"sede": str(branch.public_id)}).status_code == 200


def cash_only(amount: str) -> dict:
    return {"parts": [{"method": "efectivo"}], "received": amount}
