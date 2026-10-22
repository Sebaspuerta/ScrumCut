"""Modo "todas": los indicadores suman las sedes, y ninguna escritura se hace sin una sede (S2)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cash import services as cash
from apps.receivables import services as receivables
from apps.reports.selectors.dashboard import executive_dashboard
from apps.sales import services as sales
from apps.sales.selectors import local_today
from apps.tenancy.forms import CROSS_TAB_MESSAGE, BranchBoundForm
from tests.conftest import scope_of
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

D = Decimal


@pytest.fixture
def sold_in_both(world, norte):
    sell(world, world.ana, service=world.corte)  # 25 000 en Centro
    sell(world, world.beto, product=world.cera)  # 20 000 en Centro
    sales.quick_register(
        world.owner,
        scope_of(world.owner, norte),
        barber=world.beto.public_id,
        method="efectivo",
        service=world.barba.public_id,
    )  # 15 000 en Norte
    return norte


def _kpis(world, scope) -> dict:
    return executive_dashboard(world.owner, local_today(world.owner), scope=scope)["kpis"]


def test_los_indicadores_del_consolidado_son_la_suma_de_las_sedes(world, sold_in_both):
    centro = _kpis(world, scope_of(world.owner, world.branch))
    norte = _kpis(world, scope_of(world.owner, sold_in_both))
    todas = _kpis(world, scope_of(world.owner, everything=True))

    assert todas["income"]["value"] == centro["income"]["value"] + norte["income"]["value"] == D("60000")
    assert todas["orders"]["value"] == centro["orders"]["value"] + norte["orders"]["value"] == 3
    assert todas["cash"]["expected"] == centro["cash"]["expected"] + norte["cash"]["expected"]


def test_en_todas_las_sedes_no_se_abre_caja_ni_se_crea_comanda_ni_fiado(world, norte):
    everything = scope_of(world.owner, everything=True)

    with pytest.raises(ValidationError) as error:
        cash.open_session(world.owner, everything, opening_amount=D("0"))
    assert "branch" in error.value.message_dict
    with pytest.raises(ValidationError):
        sales.create_order(world.owner, everything)
    with pytest.raises(ValidationError):
        receivables.create_manual(world.owner, world.laura.public_id, scope=everything, total=D("1000"))


def test_el_formulario_abierto_en_otra_sede_se_rechaza(world, norte):
    opened_in_centro = {"sede_origen": scope_of(world.owner, world.branch).token}

    form = BranchBoundForm(opened_in_centro, branch_scope=scope_of(world.owner, norte))  # cambió en otra pestaña

    assert not form.is_valid()
    assert form.errors["sede_origen"] == [CROSS_TAB_MESSAGE]


def test_el_formulario_de_la_misma_sede_pasa(world):
    scope = scope_of(world.owner, world.branch)
    form = BranchBoundForm({"sede_origen": scope.token}, branch_scope=scope)
    assert form.is_valid()
    assert BranchBoundForm(branch_scope=scope).fields["sede_origen"].initial == scope.token
