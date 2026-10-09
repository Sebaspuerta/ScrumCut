"""Qué entra en un reporte: el período en la zona de la barbería y las comandas cerradas visibles.

Regla 49 con el defecto 28 corregido: los días se interpretan en `Barbershop.timezone`,
no en UTC ni en una zona fija. Comisiones y costos salen de lo copiado en cada línea
al cerrar (defectos 1, 2 y 3), así que cambiar el catálogo no reescribe el pasado.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import DecimalField, F, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from apps.sales.models import Order, OrderItem, OrderStatus
from apps.sales.selectors import day_bounds, period_dates, scoped_orders
from apps.tenancy.models import Membership

NET_SALE = F("line_total") - F("line_discount")
LINE_COST = F("unit_cost") * F("quantity") + F("consumables_cost")


@dataclass(frozen=True)
class Period:
    date_from: date
    date_to: date
    start: datetime
    end: datetime
    tz: ZoneInfo


def resolve_period(membership: Membership, date_from: date | None = None, date_to: date | None = None) -> Period:
    date_from, date_to = period_dates(membership, date_from, date_to)
    tz_name = membership.barbershop.timezone
    start, end = day_bounds(tz_name, date_from, date_to)
    return Period(date_from, date_to, start, end, ZoneInfo(tz_name))


def money_sum(expression, condition: Q | None = None) -> Coalesce:
    return Coalesce(
        Sum(expression, filter=condition),
        Value(Decimal("0.00")),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )


def closed_orders(membership: Membership, period: Period) -> QuerySet[Order]:
    """Pasa por `scoped_orders`: si un rol con alcance propio llega a ver reportes, ve solo lo suyo."""
    return scoped_orders(membership).filter(
        status=OrderStatus.CLOSED, closed_at__gte=period.start, closed_at__lt=period.end
    )


def closed_items(membership: Membership, period: Period) -> QuerySet[OrderItem]:
    return OrderItem.objects.filter(order__in=closed_orders(membership, period))
