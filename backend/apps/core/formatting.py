"""Formato colombiano de lo que arma el backend (API, Excel y alertas). React tiene el suyo en
src/lib/format.ts y los dos se prueban con los mismos casos (format-cases.json)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

MINUS = "−"  # signo menos tipográfico, como en las maquetas
MASK_MIN_DIGITS = 7
COLOMBIA_PREFIX, COLOMBIA_FULL_LENGTH = (
    "57",
    12,
)  # así guarda el celular `normalize_phone`  # con menos dígitos, mostrar inicio y final dejaría el número a la vista
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MONTH_NAMES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)  # fmt: skip
WEEKDAYS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
WEEKDAY_NAMES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def format_cop(value: Decimal | int | None) -> str:
    """Pesos sin decimales y con punto de miles: $1.250.000, −$8.000."""
    if value is None:
        return "—"
    amount = Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    digits = f"{abs(amount):,.0f}".replace(",", ".")
    return f"{MINUS if amount < 0 else ''}${digits}"


def mask_phone(phone: str | None) -> str:
    """Celular enmascarado para la pantalla: 300 *** 4512 (sin el prefijo 57 con que se guarda). Sin número, vacío."""
    digits = "".join(character for character in phone or "" if character.isdigit())
    if len(digits) == COLOMBIA_FULL_LENGTH and digits.startswith(COLOMBIA_PREFIX):
        digits = digits[len(COLOMBIA_PREFIX) :]
    if len(digits) < MASK_MIN_DIGITS:
        return ""
    return f"{digits[:3]} *** {digits[-4:]}"


def short_date(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]}"


def weekday_short(day: date) -> str:
    return WEEKDAYS[day.weekday()]


def weekday_name(day: date) -> str:
    return WEEKDAY_NAMES[day.weekday()]


def month_label(day: date) -> str:
    """Octubre 2026."""
    return f"{MONTH_NAMES[day.month - 1]} {day.year}"


def day_label(day: date) -> str:
    return f"{weekday_short(day)} {short_date(day)}"
