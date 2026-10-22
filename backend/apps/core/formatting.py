"""Formato colombiano para la interfaz: una sola implementación que usan las plantillas y los datos del JS."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

MINUS = "−"  # signo menos tipográfico, como en las maquetas
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


def format_variation(variation: dict | None, empty: str = "—") -> str:
    """▴ +12,4 % o ▾ −3,1 %; sin datos con qué comparar, `empty`."""
    if variation is None:
        return empty
    percent = variation["percent"]
    arrow = "▴" if percent >= 0 else "▾"
    sign = "+" if percent >= 0 else MINUS
    return f"{arrow} {sign}{abs(percent):.1f} %".replace(".", ",")


def format_difference(value: Decimal | None) -> str:
    """Diferencia del arqueo: Cuadrada, ▴ +$5.000 (sobra) o ▾ −$8.000 (falta). Sin rojos: signo y flecha."""
    if value is None:
        return "—"
    if not value:
        return "Cuadrada"
    return f"▴ +{format_cop(value)}" if value > 0 else f"▾ {format_cop(value)}"


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
