"""Ventas por día del tablero por alcance de sede (fase F2): cada sede ve lo suyo; "todas" suma."""

from datetime import datetime
from decimal import Decimal

import pytest

from apps.reports.selectors.calendar import sales_calendar
from apps.sales import services as sales
from apps.sales.selectors import local_today
from tests.conftest import scope_of
from tests.reports.helpers import close_at, sell

pytestmark = pytest.mark.django_db

D = Decimal


def _sell_in_norte(world, norte):
    return sales.quick_register(
        world.owner,
        scope_of(world.owner, norte),
        barber=world.ana.public_id,
        method="efectivo",
        service=world.barba.public_id,
    )


def _today_total(membership, scope) -> Decimal:
    today = local_today(membership)
    calendar = sales_calendar(membership, today, scope=scope)
    return next(cell for week in calendar["weeks"] for cell in week["days"] if cell and cell["today"])["total"]


def test_el_cajero_de_centro_no_ve_las_ventas_de_norte(world, norte):
    sell(world, world.ana, service=world.corte)  # 25 000 en Centro
    _sell_in_norte(world, norte)  # 15 000 en Norte

    assert _today_total(world.cashier, scope_of(world.cashier)) == D("25000")


def test_en_todas_cada_dia_es_la_suma_de_las_sedes(world, norte):
    first_of_month = local_today(world.owner).replace(day=1)
    close_at(sell(world, world.ana, service=world.corte), datetime.combine(first_of_month, datetime.min.time()))
    sell(world, world.ana, service=world.corte)
    _sell_in_norte(world, norte)

    everything = scope_of(world.owner, everything=True)
    centro, norte_scope = scope_of(world.owner, world.branch), scope_of(world.owner, norte)
    month = local_today(world.owner)

    def totals(scope):
        calendar = sales_calendar(world.owner, month, scope=scope)
        return [cell["total"] for week in calendar["weeks"] for cell in week["days"] if cell]

    summed = [a + b for a, b in zip(totals(centro), totals(norte_scope), strict=True)]
    assert totals(everything) == summed
    assert _today_total(world.owner, everything) == D("40000")
