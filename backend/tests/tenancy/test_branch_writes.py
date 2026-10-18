"""Fase S4a: ninguna escritura toca un objeto de otra sede, ni conociendo su public_id.

Un objeto de otra sede se trata igual que uno de otra barbería: `DoesNotExist`, para no
revelar que existe. El cajero de `world` es de Centro; Norte tiene su caja, una comanda
abierta, una cerrada y un fiado.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.cash import services as cash
from apps.cash.models import CashSession
from apps.cash.selectors import open_session_for
from apps.receivables import services as receivables
from apps.sales import services as sales
from apps.sales.models import Order, OrderStatus
from apps.tenancy.roles import Role
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

D = Decimal


@pytest.fixture
def in_norte(world, norte) -> SimpleNamespace:
    """Lo que el cajero de Centro no debe poder tocar."""
    owner_in_norte = scope_of(world.owner, norte)
    open_order = sales.create_order(world.owner, owner_in_norte, barber=world.ana.public_id)
    item = sales.add_item(world.owner, open_order.public_id, scope=owner_in_norte, service=world.corte.public_id)
    closed = sales.quick_register(
        world.owner, owner_in_norte, barber=world.ana.public_id, method="efectivo", service=world.barba.public_id
    )
    debt = receivables.create_manual(world.owner, world.laura.public_id, scope=owner_in_norte, total=D("5000"))
    return SimpleNamespace(
        session=open_session_for(norte), order=open_order, item=item, closed=closed, debt=debt, branch=norte
    )


def _cashier_writes(world, target):
    scope = scope_of(world.cashier)  # Centro
    cashier, order = world.cashier, target.order.public_id
    return {
        "cerrar caja": lambda: cash.close_session(
            cashier, target.session.public_id, scope=scope, counted_amount=D("0")
        ),
        "gasto": lambda: cash.register_manual_movement(
            cashier,
            target.session.public_id,
            scope=scope,
            kind="gasto",
            amount=D("1000"),
            payment_method="efectivo",
            description="Aseo",
        ),
        "agregar ítem": lambda: sales.add_item(cashier, order, scope=scope, service=world.corte.public_id),
        "editar ítem": lambda: sales.update_item_quantity(
            cashier, order, scope=scope, item=target.item.public_id, quantity=2
        ),
        "quitar ítem": lambda: sales.remove_item(cashier, order, scope=scope, item=target.item.public_id),
        "descuento": lambda: sales.set_discount(cashier, order, scope=scope, amount=D("1000"), reason="Amigo"),
        "en espera": lambda: sales.hold_order(cashier, order, scope=scope),
        "cerrar comanda": lambda: sales.close_order(
            cashier, order, scope=scope, payments=[{"method": "efectivo", "amount": D("25000")}]
        ),
        "anular comanda abierta": lambda: sales.cancel_order(cashier, order, scope=scope, reason="Error"),
        "abonar fiado": lambda: receivables.add_payment(
            cashier, target.debt.public_id, scope=scope, amount=D("1000"), method="efectivo"
        ),
    }


WRITES = [
    "cerrar caja",
    "gasto",
    "agregar ítem",
    "editar ítem",
    "quitar ítem",
    "descuento",
    "en espera",
    "cerrar comanda",
    "anular comanda abierta",
    "abonar fiado",
]


@pytest.mark.parametrize("write", WRITES)
def test_el_cajero_de_centro_no_toca_nada_de_norte(world, in_norte, write):
    with pytest.raises(ObjectDoesNotExist):
        _cashier_writes(world, in_norte)[write]()

    assert CashSession.objects.get(pk=in_norte.session.pk).is_open
    assert Order.objects.get(pk=in_norte.order.pk).status == OrderStatus.OPEN


def test_reanudar_una_comanda_de_otra_sede_no_la_encuentra(world, in_norte):
    sales.hold_order(world.owner, in_norte.order.public_id, scope=scope_of(world.owner, in_norte.branch))
    with pytest.raises(ObjectDoesNotExist):
        sales.resume_order(world.cashier, in_norte.order.public_id, scope=scope_of(world.cashier))


def test_desde_centro_no_se_anula_lo_cerrado_ni_el_fiado_de_norte(world, member, in_norte):
    admin = member(Role.ADMIN, world.shop)  # tiene los permisos de anular; la sede es lo que lo frena
    in_centro = scope_of(admin, world.branch)

    with pytest.raises(ObjectDoesNotExist):
        sales.cancel_order(admin, in_norte.closed.public_id, scope=in_centro, reason="Error")
    with pytest.raises(ObjectDoesNotExist):
        receivables.cancel_receivable(admin, in_norte.debt.public_id, scope=in_centro, reason="Error")


def test_en_todas_las_sedes_no_se_escribe_sobre_lo_que_existe(world, in_norte):
    everything = scope_of(world.owner, everything=True)
    with pytest.raises(ValidationError):
        sales.hold_order(world.owner, in_norte.order.public_id, scope=everything)
    with pytest.raises(ValidationError):
        cash.close_session(world.owner, in_norte.session.public_id, scope=everything, counted_amount=D("0"))


def test_en_su_propia_sede_el_dueno_si_escribe(world, in_norte):
    owner_in_norte = scope_of(world.owner, in_norte.branch)
    held = sales.hold_order(world.owner, in_norte.order.public_id, scope=owner_in_norte)
    assert held.status == OrderStatus.ON_HOLD
