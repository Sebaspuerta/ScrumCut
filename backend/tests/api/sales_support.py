"""Apoyo de las pruebas de la API: comandas, clientes y fiados creados con los services, y peticiones JSON."""

from decimal import Decimal

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.clients import services as clients
from apps.clients.models import Client as ClientRecord
from apps.receivables import services as receivables
from apps.receivables.models import Receivable
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


def sell(world, client: Client, *, customer=None) -> Order:
    """Una comanda de Centro cobrada por Nequi: una visita del cliente en la sede."""
    order = open_order(world, client=customer.public_id if customer else None)
    assert (
        post(client, "api_order_checkout", {"parts": [{"method": "nequi"}]}, public_id=order.public_id).status_code
        == 200
    )
    return order


def credit(world, customer, *, branch: Branch | None = None, total: str = "25000") -> Receivable:
    """Un fiado manual del dueño en una sede (Centro por defecto), que queda como su sede de origen."""
    scope = scope_of(world.owner, branch or world.branch)
    return receivables.create_manual(world.owner, customer.public_id, scope=scope, total=Decimal(total))


def new_client(world, name: str, phone: str = "") -> ClientRecord:
    return clients.create_client(
        world.owner, {"full_name": name, "phone": phone}, data_consent_at=timezone.now(), data_policy_version="1.0"
    )
