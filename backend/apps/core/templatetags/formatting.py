from django import template

from apps.clients.board import NO_ACTIVITY
from apps.clients.selectors import ClientStatus
from apps.core.formatting import (
    day_label,
    format_cop,
    format_difference,
    format_variation,
    mask_phone,
    month_label,
    short_date,
)
from apps.core.shell_menus import initials

register = template.Library()

register.filter("cop", format_cop)
register.filter("variation", format_variation)
register.filter("difference", format_difference)
register.filter("short_date", short_date)
register.filter("day_label", day_label)
register.filter("month_label", month_label)
register.filter("mask_phone", mask_phone)
register.filter("initials", initials)


@register.filter
def first_word(value: str) -> str:
    """El nombre de pila: "Nueva comanda para Laura"."""
    return (value or "").split(" ", 1)[0]


@register.filter
def level_label(value: str) -> str:
    """El nombre del nivel del cliente como lo define el backend (ClientStatus)."""
    if value == NO_ACTIVITY:
        return "Sin visitas en la sede"
    return ClientStatus(value).label if value in ClientStatus.values else ""
