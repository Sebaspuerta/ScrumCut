"""Decisiones 15 y 16: la persona es de la barbería; historial, fiados y nivel son de cada sede."""

from decimal import Decimal

import pytest

from apps.clients import selectors as clients
from apps.clients import services as client_services
from apps.clients.selectors import ClientStatus
from apps.receivables import selectors as receivables_selectors
from apps.receivables import services as receivables
from apps.receivables.models import Receivable
from apps.sales import selectors as sales_selectors
from apps.sales import services as sales
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

D = Decimal


def _visit(world, scope) -> None:
    """Una comanda cerrada de Laura en la sede del alcance."""
    order = sales.create_order(world.owner, scope, client=world.laura.public_id, barber=world.ana.public_id)
    sales.add_item(world.owner, order.public_id, service=world.corte.public_id)
    sales.close_order(world.owner, order.public_id, payments=[{"method": "efectivo", "amount": D("25000")}])


@pytest.fixture
def laura_in_centro(world, norte):
    centro = scope_of(world.owner, world.branch)
    for _ in range(3):  # tres visitas: frecuente con los umbrales por defecto
        _visit(world, centro)
    return centro, scope_of(world.owner, norte)


def test_la_misma_persona_tiene_un_nivel_distinto_en_cada_sede(world, laura_in_centro):
    centro, norte = laura_in_centro

    in_centro = clients.client_profile(world.owner, world.laura.public_id, scope=centro)
    in_norte = clients.client_profile(world.owner, world.laura.public_id, scope=norte)

    assert (in_centro["visits"], in_centro["status"]) == (3, ClientStatus.FREQUENT)
    assert (in_norte["visits"], in_norte["status"]) == (0, ClientStatus.NEW)


def test_una_sede_no_ve_el_historial_de_otra(world, laura_in_centro):
    centro, norte = laura_in_centro
    order = sales_selectors.list_orders(world.owner, scope=centro).object_list[0]

    assert len(sales_selectors.list_orders(world.owner, scope=centro).object_list) == 3
    assert not sales_selectors.list_orders(world.owner, scope=norte).object_list
    with pytest.raises(type(order).DoesNotExist):
        sales_selectors.get_order(world.owner, order.public_id, scope=norte)


def test_una_sede_no_ve_los_fiados_de_otra_ni_su_deuda(world, laura_in_centro):
    centro, norte = laura_in_centro
    debt = receivables.create_manual(world.owner, world.laura.public_id, scope=centro, total=D("30000"))

    assert list(receivables_selectors.list_receivables(world.owner, scope=centro)) == [debt]
    assert not receivables_selectors.list_receivables(world.owner, scope=norte).exists()
    with pytest.raises(Receivable.DoesNotExist):
        receivables_selectors.get_receivable(world.owner, debt.public_id, scope=norte)
    profile = clients.client_profile(world.owner, world.laura.public_id, scope=norte)
    assert (profile["balance"], profile["status"]) == (D("0"), ClientStatus.NEW)


def test_cualquier_sede_encuentra_a_la_persona_por_documento(world, norte):
    pedro = client_services.create_client(
        world.owner,
        {"full_name": "Pedro Pérez", "document": "1.020.304.050"},
        data_consent_at=world.laura.data_consent_at,
        data_policy_version="2026-10",
    )
    receivables.create_manual(world.owner, pedro.public_id, scope=scope_of(world.owner, norte), total=D("1000"))

    assert list(clients.list_clients(world.cashier, "1020304050")) == [pedro]  # el cajero es de Centro
