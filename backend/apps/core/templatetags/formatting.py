from django import template

from apps.core.formatting import (
    day_label,
    format_cop,
    format_difference,
    format_variation,
    mask_phone,
    month_label,
    short_date,
)

register = template.Library()

register.filter("cop", format_cop)
register.filter("variation", format_variation)
register.filter("difference", format_difference)
register.filter("short_date", short_date)
register.filter("day_label", day_label)
register.filter("month_label", month_label)
register.filter("mask_phone", mask_phone)
