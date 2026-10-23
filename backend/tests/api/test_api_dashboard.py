"""`dashboard`: el tablero ejecutivo por la API, con el alcance de sede y los permisos de la pantalla en plantillas."""

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.cash import services as cash
from apps.sales import services as sales
from apps.tenancy import services as tenancy
from apps.tenancy.middleware import BRANCH_SESSION_KEY
from apps.tenancy.models import Barbershop
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.frontend.conftest import logged_in_with_mfa
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

EXTRA_BRANCHES = ("Sur", "Occidente")


def _dashboard(client, **params) -> dict:
    response = client.get(reverse("api_dashboard"), params)
    assert response.status_code == 200
    return response.json()


def _sell_in(world, branch) -> None:
    sales.quick_register(
        world.owner,
        scope_of(world.owner, branch),
        barber=world.ana.public_id,
        method="efectivo",
        service=world.barba.public_id,
    )


def test_el_cajero_de_centro_no_ve_las_ventas_ni_la_caja_de_norte(world, norte, cashier_client, owner_client):
    sell(world, world.ana, service=world.corte)  # 25 000 en Centro
    _sell_in(world, norte)  # 15 000 en Norte

    mine = _dashboard(cashier_client)
    owner_client.post(reverse("api_branch"), {"sede": "todas"}, content_type="application/json")
    everything = _dashboard(owner_client)

    assert mine["scope_label"] == "Centro"
    assert Decimal(mine["calendar"]["total"]) == Decimal("25000")
    assert Decimal(everything["calendar"]["total"]) == Decimal("40000")
    assert "Norte" not in str(mine)


def test_en_todas_la_caja_pide_elegir_una_sede(world, norte, owner_client):
    owner_client.post(reverse("api_branch"), {"sede": "todas"}, content_type="application/json")

    cash = _dashboard(owner_client)["cash"]

    assert cash == {"needs_branch": True, "flow": None}


def test_en_una_sede_el_cuadre_va_de_la_apertura_al_esperado(world, cashier_client):
    sell(world, world.ana, service=world.corte)

    flow = _dashboard(cashier_client)["cash"]["flow"]

    assert [step["label"] for step in flow["steps"]][0] == "Apertura"
    assert Decimal(flow["expected"]) == Decimal("75000")  # base 50 000 + 25 000 en efectivo
    assert flow["is_open"] is True


@pytest.mark.parametrize(("role", "status"), [(Role.BARBER, 403), (Role.VIEWER, 200), (Role.CASHIER, 200)])
def test_exige_reportes_ver(world, member, role, status):
    client = logged_in_with_mfa(member(role, world.shop, email=f"otro-{role}@a.test").user)
    assert client.get(reverse("api_dashboard")).status_code == status


def test_un_mes_que_no_vale_vuelve_al_mes_actual(world, cashier_client):
    current = _dashboard(cashier_client)
    data = _dashboard(cashier_client, mes="1999-01")

    assert data["month"] == current["month"]
    assert data["next_month"] is None


def _queries(client) -> int:
    client.get(reverse("api_dashboard"))
    with CaptureQueriesContext(connection) as context:
        assert client.get(reverse("api_dashboard")).status_code == 200
    return len(context.captured_queries)


@pytest.mark.parametrize("mode", ["una", "todas"])
def test_las_consultas_son_las_mismas_con_una_sede_que_con_tres(world, owner_client, mode):
    sell(world, world.ana, service=world.corte)
    session = owner_client.session
    session[BRANCH_SESSION_KEY] = "todas" if mode == "todas" else str(world.branch.public_id)
    session.save()
    with_one = _queries(owner_client)

    Barbershop.objects.filter(pk=world.shop.pk).update(max_branches=len(EXTRA_BRANCHES) + 1)
    world.owner.barbershop.refresh_from_db()
    for name in EXTRA_BRANCHES:
        branch = tenancy.create_branch(world.owner, {"name": name})
        both = [world.branch.public_id, branch.public_id]
        tenancy.set_barber_branches(world.owner, world.ana.public_id, branches=both)
        cash.open_session(world.owner, scope_of(world.owner, branch), opening_amount=Decimal("0"))
        _sell_in(world, branch)

    assert _queries(owner_client) == with_one
