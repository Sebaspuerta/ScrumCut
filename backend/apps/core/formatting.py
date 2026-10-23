"""Formato colombiano para la interfaz: una sola implementación que usan las plantillas y los datos del JS."""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

MINUS = "−"  # signo menos tipográfico, como en las maquetas
NOON = 12
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


def clock(moment: datetime) -> str:
    """8:00 a. m. / 3:15 p. m. (hora local ya convertida)."""
    suffix = "a. m." if moment.hour < NOON else "p. m."
    return f"{(moment.hour - 1) % NOON + 1}:{moment.minute:02d} {suffix}"


def opened_since(moment: datetime, today: date) -> str:
    """Desde cuándo está abierta una caja: "desde las 8:00 a. m.", "desde ayer, 8:00 a. m." o
    "desde el lun 19 oct, 8:00 a. m."."""
    if moment.date() == today:
        return f"desde las {clock(moment)}"
    if moment.date() == today - timedelta(days=1):
        return f"desde ayer, {clock(moment)}"
    return f"desde el {weekday_short(moment.date()).lower()} {short_date(moment.date())}, {clock(moment)}"
