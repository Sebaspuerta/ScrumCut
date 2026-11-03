"""Formato colombiano: lo que formatea el backend (API, Excel y alertas) es igual a lo de la app de React."""

import json
from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings

from apps.core.formatting import day_label, format_cop, mask_phone, month_label, short_date

D = Decimal
# Los mismos casos prueba la app de React (frontend/app/src/lib/format.test.ts): un solo formato en los dos lados.
# La hora y el "desde cuándo" de la caja solo los formatea React; sus casos los prueba solo Vitest.
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
