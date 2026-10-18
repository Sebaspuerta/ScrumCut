"""Toda lectura de un objeto por su public_id va por el alcance, igual que las escrituras (S4a).

Un objeto de otra sede responde `DoesNotExist`, igual que uno de otra barbería.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ObjectDoesNotExist

from apps.cash.selectors import open_session_for, session_summary
from apps.receivables import services as receivables
from apps.receivables.selectors import get_receivable
from apps.sales import services as sales
from apps.sales.selectors import barber_performance, get_order
from apps.staff import services as staff
from apps.staff.selectors import get_barber
from apps.tenancy.roles import Role
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db


@pytest.fixture
def from_norte(world, norte):
    in_norte = scope_of(world.owner, norte)
    order = sales.create_order(world.owner, in_norte)
    debt = receivables.create_manual(world.owner, world.laura.public_id, scope=in_norte, total=Decimal("5000"))
    barber = staff.create_barber(
        world.owner,
        {"display_name": "Nico"},
        commission_type="percentage",
        commission_value=40,
        branches=[norte.public_id],
    )
    return {"session": open_session_for(norte), "order": order, "debt": debt, "barber": barber}


@pytest.mark.parametrize("read", ["resumen de caja", "comanda", "fiado"])
def test_el_cajero_de_centro_no_lee_nada_de_norte_por_su_codigo(world, from_norte, read):
    cashier, centro = world.cashier, scope_of(world.cashier)
    readers = {
        "resumen de caja": lambda: session_summary(cashier, from_norte["session"].public_id, scope=centro),
        "comanda": lambda: get_order(cashier, from_norte["order"].public_id, scope=centro),
        "fiado": lambda: get_receivable(cashier, from_norte["debt"].public_id, scope=centro),
    }
    with pytest.raises(ObjectDoesNotExist):
        readers[read]()


def test_desde_centro_no_se_lee_un_barbero_que_solo_trabaja_en_norte(world, member, from_norte):
    admin = member(Role.ADMIN, world.shop)
    centro = scope_of(admin, world.branch)

    with pytest.raises(ObjectDoesNotExist):
        get_barber(admin, from_norte["barber"].public_id, scope=centro)
    with pytest.raises(ObjectDoesNotExist):
        barber_performance(admin, from_norte["barber"].public_id, scope=centro)


def test_en_todas_las_sedes_se_lee_lo_de_cualquier_sede(world, from_norte):
    everything = scope_of(world.owner, everything=True)

    assert session_summary(world.owner, from_norte["session"].public_id, scope=everything)["session"]
    assert get_order(world.owner, from_norte["order"].public_id, scope=everything) == from_norte["order"]
    assert get_barber(world.owner, from_norte["barber"].public_id, scope=everything) == from_norte["barber"]
