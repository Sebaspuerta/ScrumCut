"""Producción de los barberos: la única agregación de líneas por barbero (regla 50 y fase S5 de docs/sedes.md).

El dinero se reparte por línea: cada barbero suma la venta neta de las líneas que hizo, nunca el
total de la comanda. Una comanda con dos barberos cuenta como una comanda para cada uno. Solo las
líneas con barbero: un producto vendido sin barbero no es producción de nadie.
"""

from decimal import Decimal

from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from apps.reports.scope import NET_SALE, Period, closed_items, display_name, money_sum
from apps.sales.models import ItemType
from apps.tenancy.models import Membership

BARBER_FIELDS = ("barber__public_id", "barber__display_name", "barber__deleted_at")


def _grouped(membership: Membership, period: Period, *fields: str) -> QuerySet:
    """Una sola consulta agregada por barbero (y por lo que se agregue en `fields`)."""
    return (
        closed_items(membership, period)
        .filter(barber__isnull=False)
        .values(*fields, *BARBER_FIELDS)
        .annotate(
            orders=Count("order", distinct=True),
            services=Coalesce(Sum("quantity", filter=Q(item_type=ItemType.SERVICE)), 0),
            sales=money_sum(NET_SALE),
            commission=money_sum("commission_amount"),
        )
    )


def _row(row: dict) -> dict:
    return {
        "barber": row["barber__public_id"],
        "name": display_name(row["barber__display_name"], row["barber__deleted_at"]),
        "orders": row["orders"],
        "services": row["services"],
        "sales": row["sales"],
        "commission": row["commission"],
    }


def barber_sales(membership: Membership, period: Period) -> list[dict]:
    """Por barbero en las sedes del período; en "todas", sumadas. Quien llama ya validó el permiso."""
    rows = _grouped(membership, period).order_by("-sales", "barber__display_name")
    return [_row(row) for row in rows]


def barber_production(membership: Membership, period: Period) -> dict:
    """Por (sede, barbero), con su Total, que es la suma de las filas.

    Como cada barbero cuenta una vez cada comanda en la que trabajó, el Total de comandas puede
    pasar del número de comandas cerradas. Lo llama `branch_comparison`, que ya validó permisos y alcance.
    """
    grouped = _grouped(membership, period, "order__branch__name").order_by(
        "order__branch__name", "-sales", "barber__display_name"
    )
    rows = [{"branch": row["order__branch__name"], **_row(row), "total": row["sales"]} for row in grouped]
    total_sales = sum((row["total"] for row in rows), Decimal("0.00"))
    return {"rows": rows, "total": {"orders": sum(row["orders"] for row in rows), "total": total_sales}}
