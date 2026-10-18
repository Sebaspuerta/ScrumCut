"""Sede de los fiados y de los abonos, y sede activa obligatoria para el dinero (decisiones 3 y 14).

Un fiado se abona solo en su sede de origen: ninguna operación de dinero cruza sedes.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cash import selectors as cash_selectors
from apps.cash import services as cash
from apps.receivables import services as receivables
from apps.receivables.models import Receivable
from apps.reports.selectors.cash import cash_movements
from apps.sales import services as sales
from apps.tenancy import services as tenancy
from apps.tenancy.branch_scope import INACTIVE_BRANCH
from apps.tenancy.models import Branch
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

D = Decimal


def _manual_debt(world, branch: Branch):
    return receivables.create_manual(
        world.owner, world.laura.public_id, total=D("30000"), scope=scope_of(world.owner, branch)
    )


def test_el_fiado_manual_guarda_la_sede_activa_al_crearlo(world):
    assert _manual_debt(world, world.branch).origin_branch == world.branch


def test_el_fiado_de_una_comanda_guarda_la_sede_de_la_comanda(world, norte):
    order = sales.create_order(world.owner, scope_of(world.owner, norte), client=world.laura.public_id)
    sales.add_item(
        world.owner,
        order.public_id,
        service=world.corte.public_id,
        barber=world.ana.public_id,
        scope=scope_of(world.owner, norte),
    )
    sales.close_order(world.owner, order.public_id, as_credit=True, scope=scope_of(world.owner, norte))

    assert Receivable.objects.get(order=order).origin_branch == norte


def _paid_in(world, branch: Branch) -> list[Decimal]:
    return [
        row["amount"]
        for row in cash_movements(world.owner, scope=scope_of(world.owner, branch))
        if row["kind"] == "abono_fiado"
    ]


def test_un_fiado_de_centro_no_se_abona_en_la_caja_de_norte(world, norte):
    debt = _manual_debt(world, world.branch)

    # Desde Norte el fiado de Centro no se encuentra, igual que uno de otra barbería (fase S4a).
    with pytest.raises(Receivable.DoesNotExist):
        receivables.add_payment(
            world.owner, debt.public_id, amount=D("10000"), method="efectivo", scope=scope_of(world.owner, norte)
        )

    debt.refresh_from_db()
    assert debt.balance == D("30000") and not debt.payments.exists()
    assert _paid_in(world, norte) == []


def test_un_fiado_se_abona_en_su_sede_y_el_dinero_queda_en_su_caja(world, norte):
    debt = _manual_debt(world, world.branch)

    receivables.add_payment(
        world.owner, debt.public_id, amount=D("10000"), method="efectivo", scope=scope_of(world.owner, world.branch)
    )

    assert _paid_in(world, world.branch) == [D("10000")]
    assert _paid_in(world, norte) == []
    assert debt.payments.get().cash_movement.session == world.session


def test_un_abono_no_entra_a_una_sede_desactivada(world, norte):
    debt = _manual_debt(world, norte)
    opened_in_norte = scope_of(world.owner, norte)  # la petición empezó con Norte activa
    cash.close_session(
        world.owner,
        cash_selectors.open_session_for(norte).public_id,
        counted_amount=D("0"),
        scope=opened_in_norte,
    )
    tenancy.deactivate_branch(world.owner, norte.public_id)

    with pytest.raises(ValidationError) as error:
        receivables.add_payment(world.owner, debt.public_id, amount=D("1000"), method="efectivo", scope=opened_in_norte)
    assert error.value.message_dict["branch"] == [INACTIVE_BRANCH]


def test_un_fiado_manual_no_nace_en_una_sede_desactivada(world, norte):
    opened_in_norte = scope_of(world.owner, norte)
    cash.close_session(
        world.owner,
        cash_selectors.open_session_for(norte).public_id,
        counted_amount=D("0"),
        scope=opened_in_norte,
    )
    tenancy.deactivate_branch(world.owner, norte.public_id)

    with pytest.raises(ValidationError):
        receivables.create_manual(world.owner, world.laura.public_id, scope=opened_in_norte, total=D("30000"))


def test_una_sede_desactivada_no_tiene_caja_vigente(world, norte):
    session = cash_selectors.open_session_for(norte)
    opened_in_norte = scope_of(world.owner, norte)  # la petición empezó con Norte activa
    Branch.objects.filter(pk=norte.pk).update(is_active=False)  # sin el servicio, que exige cerrar antes

    assert cash_selectors.current_session(world.owner, scope=opened_in_norte) is None
    assert cash_selectors.current_session(world.owner, scope=scope_of(world.owner, world.branch)) == world.session
    assert session is not None
