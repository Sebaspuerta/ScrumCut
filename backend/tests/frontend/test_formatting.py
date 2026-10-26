"""Formato colombiano de la interfaz: una sola implementación para plantillas y datos del JS."""

import json
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.template import Context, Template

from apps.core.formatting import (
    clock,
    day_label,
    format_cop,
    format_difference,
    format_variation,
    mask_phone,
    month_label,
    opened_since,
    short_date,
)

D = Decimal
# Los mismos casos prueba la app de React (frontend/app/src/lib/format.test.ts): un solo formato en los dos lados.
SHARED = json.loads((settings.FRONTEND_DIR / "app" / "src" / "lib" / "format-cases.json").read_text(encoding="utf-8"))


def _cop_input(value: str | int | None) -> Decimal | int | None:
    return D(value) if isinstance(value, str) else value


@pytest.mark.parametrize(("value", "expected"), SHARED["cop"])
def test_pesos_colombianos(value, expected):
    assert format_cop(_cop_input(value)) == expected


@pytest.mark.parametrize(("value", "expected"), SHARED["short_date"])
def test_fecha_corta_igual_que_en_la_app_de_react(value, expected):
    assert short_date(date.fromisoformat(value)) == expected


@pytest.mark.parametrize(("value", "expected"), SHARED["day_label"])
def test_dia_igual_que_en_la_app_de_react(value, expected):
    assert day_label(date.fromisoformat(value)) == expected


@pytest.mark.parametrize(("value", "expected"), SHARED["month_label"])
def test_mes_igual_que_en_la_app_de_react(value, expected):
    assert month_label(date.fromisoformat(value)) == expected


@pytest.mark.parametrize(("value", "zone", "expected"), SHARED["clock"])
def test_hora_igual_que_en_la_app_de_react(value, zone, expected):
    assert clock(datetime.fromisoformat(value).astimezone(ZoneInfo(zone))) == expected


@pytest.mark.parametrize(("value", "today", "zone", "expected"), SHARED["opened_since"])
def test_desde_cuando_esta_abierta_la_caja_igual_que_en_la_app_de_react(value, today, zone, expected):
    moment = datetime.fromisoformat(value).astimezone(ZoneInfo(zone))
    assert opened_since(moment, date.fromisoformat(today)) == expected


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


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("573001234567", "300 *** 4567"),  # como lo guarda normalize_phone
        ("300 123 4567", "300 *** 4567"),
        ("12345", ""),  # con tan pocos dígitos no se muestra
        ("", ""),
    ],
)
def test_el_celular_se_enmascara_sin_el_prefijo_57(phone, expected):
    assert mask_phone(phone) == expected
