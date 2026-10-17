"""La auditoría guarda la sede del evento cuando aplica (AuditLog.branch, docs/sedes.md)."""

from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.receivables import services as receivables
from apps.sales import services as sales
from apps.tenancy import services as tenancy
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db


def _branch_of(action: str, entity_id) -> object:
    return AuditLog.objects.filter(action=action, entity_id=str(entity_id)).latest("pk").branch


def test_caja_y_comanda_quedan_con_su_sede(world, norte):
    order = sales.create_order(world.owner, scope_of(world.owner, norte))

    assert _branch_of("caja.abrir", world.session.public_id) == world.branch
    assert _branch_of("comanda.crear", order.public_id) == norte


def test_el_fiado_y_su_abono_quedan_con_la_sede_de_origen(world):
    debt = receivables.create_manual(
        world.cashier, world.laura.public_id, total=Decimal("30000"), scope=scope_of(world.cashier, world.branch)
    )
    receivables.add_payment(
        world.cashier,
        debt.public_id,
        amount=Decimal("1000"),
        method="efectivo",
        scope=scope_of(world.cashier, world.branch),
    )

    assert _branch_of("fiado.crear", debt.public_id) == world.branch
    assert _branch_of("fiado.abonar", debt.public_id) == world.branch


def test_los_eventos_de_sede_la_llevan_y_los_de_acceso_no(world, norte):
    tenancy.set_cashier_branches(world.owner, world.cashier.public_id, branches=[norte.public_id])

    assert _branch_of("sede.crear", norte.public_id) == norte
    assert _branch_of("sede.acceso_cajero", world.cashier.public_id) is None
