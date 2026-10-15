"""Sede de los fiados y de los abonos, y sede activa obligatoria para el dinero (decisiones 3 y 14)."""

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
from apps.tenancy.models import Branch

pytestmark = pytest.mark.django_db

D = Decimal


def _manual_debt(world, branch: Branch):
    return receivables.create_manual(world.cashier, world.laura.public_id, total=D("30000"), branch=branch.public_id)


def test_el_fiado_manual_guarda_la_sede_activa_al_crearlo(world):
    assert _manual_debt(world, world.branch).origin_branch == world.branch


def test_el_fiado_de_una_comanda_guarda_la_sede_de_la_comanda(world, norte):
    order = sales.create_order(world.cashier, norte.public_id, client=world.laura.public_id)
    sales.add_item(world.cashier, order.public_id, service=world.corte.public_id, barber=world.ana.public_id)
    sales.close_order(world.cashier, order.public_id, as_credit=True)

    assert Receivable.objects.get(order=order).origin_branch == norte


def test_un_abono_de_un_fiado_de_centro_cobrado_en_norte_aparece_en_norte(world, norte):
    debt = _manual_debt(world, world.branch)

    receivables.add_payment(world.cashier, debt.public_id, amount=D("10000"), method="efectivo", branch=norte.public_id)

    def paid_in(branch):
        rows = cash_movements(world.owner, branch=branch)
        return [row["amount"] for row in rows if row["kind"] == "abono_fiado"]

    assert paid_in(norte) == [D("10000")]
    assert paid_in(world.branch) == []
    assert debt.payments.get().cash_movement.session.branch == norte


def test_un_abono_no_entra_a_una_sede_desactivada(world, norte):
    debt = _manual_debt(world, world.branch)
    cash.close_session(world.cashier, cash_selectors.open_session_for(norte).public_id, counted_amount=D("0"))
    tenancy.deactivate_branch(world.owner, norte.public_id)

    with pytest.raises(ValidationError) as error:
        receivables.add_payment(
            world.cashier, debt.public_id, amount=D("1000"), method="efectivo", branch=norte.public_id
        )
    assert "branch" in error.value.message_dict


def test_un_fiado_manual_no_nace_en_una_sede_desactivada(world, norte):
    cash.close_session(world.cashier, cash_selectors.open_session_for(norte).public_id, counted_amount=D("0"))
    tenancy.deactivate_branch(world.owner, norte.public_id)

    with pytest.raises(ValidationError):
        _manual_debt(world, norte)


def test_una_sede_desactivada_no_tiene_caja_vigente(world, norte):
    session = cash_selectors.open_session_for(norte)
    Branch.objects.filter(pk=norte.pk).update(is_active=False)  # sin el servicio, que exige cerrar antes

    assert cash_selectors.current_session(world.owner, norte.public_id) is None
    assert cash_selectors.current_session(world.owner, world.branch.public_id) == world.session
    assert session is not None
