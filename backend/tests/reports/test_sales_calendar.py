"""Ventas por día del mes (tablero, fase F2): forma del calendario, días futuros, zona horaria y consultas."""

from datetime import date, datetime
from decimal import Decimal
from unittest import mock

import pytest

from apps.reports.selectors.calendar import sales_calendar
from tests.conftest import scope_of
from tests.reports.helpers import BOGOTA, close_at, sell

pytestmark = pytest.mark.django_db

D = Decimal
OCTOBER = date(2026, 10, 1)  # empieza en jueves
TODAY = datetime(2026, 10, 14, 12, tzinfo=BOGOTA)  # miércoles 14


def _today():
    return mock.patch("django.utils.timezone.now", return_value=TODAY)


def _calendar(w, month=OCTOBER):
    with _today():
        return sales_calendar(w.owner, month, scope=scope_of(w.owner, w.branch))


def _cells(calendar) -> list:
    return [cell for week in calendar["weeks"] for cell in week["days"]]


def _day(calendar, number: int) -> dict:
    return next(cell for cell in _cells(calendar) if cell and cell["day"] == number)


def test_un_mes_que_empieza_en_jueves_deja_tres_casillas_vacias_al_inicio(world):
    first_week = _calendar(world)["weeks"][0]["days"]
    assert first_week[:3] == [None, None, None]
    assert first_week[3]["day"] == 1
    assert all(len(week["days"]) == 7 for week in _calendar(world)["weeks"])


def test_febrero_de_2028_tiene_29_dias(world):
    days = [cell["day"] for cell in _cells(_calendar(world, date(2028, 2, 1))) if cell]
    assert days == list(range(1, 30))


def test_los_dias_futuros_salen_vacios_y_hoy_marcado(world):
    calendar = _calendar(world)
    assert _day(calendar, 14)["today"] and not _day(calendar, 14)["future"]
    assert all(_day(calendar, number)["future"] for number in range(15, 32))
    assert not any(_day(calendar, number)["future"] for number in range(1, 15))


def test_una_venta_a_las_once_y_media_de_la_noche_cuenta_para_ese_dia(world):
    close_at(sell(world, world.ana, service=world.corte), datetime(2026, 10, 5, 23, 30))  # hora de Bogotá

    calendar = _calendar(world)

    assert (_day(calendar, 5)["total"], _day(calendar, 6)["total"]) == (D("25000"), D("0"))


def test_semana_tonos_y_cifras_del_mes(world):
    close_at(sell(world, world.ana, service=world.corte), datetime(2026, 10, 5, 12))  # lunes, 25 000
    close_at(sell(world, world.beto, service=world.barba), datetime(2026, 10, 7, 12))  # miércoles, 15 000
    close_at(sell(world, world.beto, service=world.barba), datetime(2026, 10, 12, 12))  # lunes siguiente

    calendar = _calendar(world)

    assert calendar["weeks"][1]["total"] == D("40000")  # del lunes 5 al domingo 11
    assert (_day(calendar, 5)["level"], _day(calendar, 7)["level"]) == (4, 2)  # 15 000 / 25 000 = 0,6
    assert (calendar["total"], calendar["selling_days"]) == (D("55000"), 3)
    assert (calendar["best"]["date"], calendar["last_sale"]["date"]) == (date(2026, 10, 5), date(2026, 10, 12))
    assert calendar["daily_average"] == D("55000") / 3
    assert [day["average"] for day in calendar["weekdays"]][:3] == [D("20000"), None, D("15000")]


def test_un_mes_sin_ventas_sale_en_ceros(world):
    calendar = _calendar(world, date(2026, 9, 1))
    assert (calendar["total"], calendar["selling_days"], calendar["best"], calendar["daily_average"]) == (
        D("0"),
        0,
        None,
        None,
    )
    assert all(cell["level"] == 0 and not cell["has_sales"] for cell in _cells(calendar) if cell)


# Una consulta agregada por día del mes, sea cual sea el número de días que vendieron.
CALENDAR_QUERIES = 1


@pytest.mark.parametrize("selling_days", [1, 6])
def test_las_consultas_no_dependen_de_los_dias_con_ventas(world, django_assert_num_queries, selling_days):
    for day in range(1, selling_days + 1):
        close_at(sell(world, world.ana, service=world.corte), datetime(2026, 10, day, 12))
    scope = scope_of(world.owner, world.branch)

    with _today(), django_assert_num_queries(CALENDAR_QUERIES):
        calendar = sales_calendar(world.owner, OCTOBER, scope=scope)

    assert calendar["selling_days"] == selling_days
