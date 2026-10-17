"""Reportes de ventas (reglas 49 a 51). Cada uno es una sola consulta agregada (defecto 27)."""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import Coalesce, TruncDate

from apps.reports.scope import LINE_COST, NET_SALE, closed_items, closed_orders, money_sum, resolve_period
from apps.sales.models import ItemType
from apps.sales.selectors import DELETED_SUFFIX
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

_EMPTY_DAY = {"orders": 0, "subtotal": Decimal("0.00"), "discount": Decimal("0.00"), "total": Decimal("0.00")}


def _name(name: str | None, deleted_at) -> str | None:
    return name + DELETED_SUFFIX if name and deleted_at else name


def sales_by_period(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> list[dict]:
    """Una fila por cada día local del período, con 0 los días sin ventas."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    rows = (
        closed_orders(membership, period)
        .annotate(day=TruncDate("closed_at", tzinfo=period.tz))
        .values("day")
        .annotate(
            orders=Count("pk"),
            subtotal=money_sum("subtotal"),
            discount=money_sum("discount"),
            total=money_sum("total"),
        )
        .order_by("day")
    )
    with_sales = {row["day"]: row for row in rows}
    days = (period.date_from + timedelta(days=n) for n in range((period.date_to - period.date_from).days + 1))
    return [with_sales.get(day, {"day": day, **_EMPTY_DAY}) for day in days]


def sales_by_barber(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> list[dict]:
    """Regla 50: ventas netas y comisión de cada barbero, tal como quedaron al cerrar."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    rows = (
        closed_items(membership, period)
        .filter(barber__isnull=False)
        .values("barber__public_id", "barber__display_name", "barber__deleted_at")
        .annotate(
            orders=Count("order", distinct=True),
            services=Coalesce(Sum("quantity", filter=Q(item_type=ItemType.SERVICE)), 0),
            sales=money_sum(NET_SALE),
            commission=money_sum("commission_amount"),
        )
        .order_by("-sales", "barber__display_name")
    )
    return [
        {
            "barber": row["barber__public_id"],
            "name": _name(row["barber__display_name"], row["barber__deleted_at"]),
            "orders": row["orders"],
            "services": row["services"],
            "sales": row["sales"],
            "commission": row["commission"],
        }
        for row in rows
    ]


def top_products(
    membership: Membership,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 10,
    *,
    scope: BranchScope,
) -> list[dict]:
    """Regla 51: por cantidad vendida, con lo vendido y su costo copiado al cerrar."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    rows = (
        closed_items(membership, period)
        .filter(item_type=ItemType.PRODUCT)
        .values("product__public_id", "product__name", "product__deleted_at")
        # "units" y no "quantity": ese nombre taparía el campo que usa LINE_COST.
        .annotate(units=Sum("quantity"), sales=money_sum(NET_SALE), cost=money_sum(LINE_COST))
        .order_by("-units", "product__name")[:limit]
    )
    return [
        {
            "product": row["product__public_id"],
            "name": _name(row["product__name"], row["product__deleted_at"]),
            "quantity": row["units"],
            "sales": row["sales"],
            "cost": row["cost"],
        }
        for row in rows
    ]


def _share(part: Decimal, total: Decimal) -> Decimal:
    return (part * 100 / total).quantize(Decimal("1")) if total else Decimal("0")


def income_mix(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> dict:
    """Ventas netas de servicios y de productos del período, con su parte del total."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    totals = closed_items(membership, period).aggregate(
        services=money_sum(NET_SALE, Q(item_type=ItemType.SERVICE)),
        products=money_sum(NET_SALE, Q(item_type=ItemType.PRODUCT)),
    )
    total = totals["services"] + totals["products"]
    return {
        "total": total,
        "services": {"amount": totals["services"], "percent": _share(totals["services"], total)},
        "products": {"amount": totals["products"], "percent": _share(totals["products"], total)},
    }


def _lines(membership: Membership, date_from: date | None, date_to: date | None, scope: BranchScope) -> QuerySet:
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    return closed_items(membership, period).annotate(net=NET_SALE).order_by("order__closed_at", "order__number", "pk")


def sale_lines(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> QuerySet:
    """Regla 55: cada línea vendida con su costo (producto o insumos) y su comisión."""
    return _lines(membership, date_from, date_to, scope).values(
        "order__closed_at",
        "order__number",
        "item_type",
        "name",
        "barber__display_name",
        "quantity",
        "unit_price",
        "line_total",
        "line_discount",
        "net",
        "commission_amount",
        cost=LINE_COST,
    )


def commission_lines(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> QuerySet:
    """Cada servicio con la comisión que se copió al cerrar: tipo, valor y monto."""
    return (
        _lines(membership, date_from, date_to, scope)
        .filter(item_type=ItemType.SERVICE)
        .values(
            "order__closed_at",
            "order__number",
            "barber__display_name",
            "name",
            "quantity",
            "net",
            "commission_type",
            "commission_rate",
            "commission_amount",
        )
    )
