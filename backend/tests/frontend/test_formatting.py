"""Formato colombiano de la interfaz: una sola implementación para plantillas y datos del JS."""

from datetime import date
from decimal import Decimal

import pytest
from django.template import Context, Template

from apps.core.formatting import day_label, format_cop, format_difference, format_variation, short_date

D = Decimal


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (D("1250000"), "$1.250.000"),
        (D("65300.50"), "$65.301"),  # sin decimales, redondeo comercial
        (D("0"), "$0"),
        (D("-8000"), "−$8.000"),
        (845, "$845"),
        (None, "—"),
    ],
)
def test_pesos_colombianos(value, expected):
    assert format_cop(value) == expected


def test_el_filtro_de_plantilla_usa_el_mismo_formato():
    rendered = Template("{% load formatting %}{{ value|cop }}").render(Context({"value": D("2480000")}))
    assert rendered == "$2.480.000"


def test_variacion_con_flecha_signo_y_coma_decimal():
    assert format_variation({"percent": D("12.4")}) == "▴ +12,4 %"
    assert format_variation({"percent": D("-3.1")}) == "▾ −3,1 %"
    assert format_variation(None) == "—"


def test_diferencia_del_arqueo_sin_rojos():
    assert format_difference(D("0")) == "Cuadrada"
    assert format_difference(D("5000")) == "▴ +$5.000"
    assert format_difference(D("-8000")) == "▾ −$8.000"


def test_fechas_cortas_en_espanol():
    assert short_date(date(2026, 10, 3)) == "3 oct"
    assert day_label(date(2026, 10, 9)) == "Vie 9 oct"
