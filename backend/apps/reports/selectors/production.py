"""Producción de cada barbero en cada sede (fase S5 de docs/sedes.md), en una sola consulta agregada."""

from decimal import Decimal

from django.db.models import Count

from apps.reports.scope import NET_SALE, Period, closed_items, money_sum
from apps.reports.selectors.sales import display_name
from apps.tenancy.models import Membership


def barber_production(membership: Membership, period: Period) -> dict:
    """Comandas y ventas netas por (sede, barbero), y su Total, que es la suma de las filas.

    Solo las líneas con barbero: un producto vendido sin barbero no es producción de nadie, como en
    `sales_by_barber`. Una comanda con dos barberos cuenta para cada uno, así que el Total de comandas puede pasar
    del número de comandas cerradas. Lo llama `branch_comparison`, que ya validó permisos y alcance.
    """
    grouped = (
        closed_items(membership, period)
        .filter(barber__isnull=False)
        .values("order__branch__name", "barber__public_id", "barber__display_name", "barber__deleted_at")
        .annotate(orders=Count("order", distinct=True), total=money_sum(NET_SALE))
        .order_by("order__branch__name", "-total", "barber__display_name")
    )
    rows = [
        {
            "branch": row["order__branch__name"],
            "barber": row["barber__public_id"],
            "name": display_name(row["barber__display_name"], row["barber__deleted_at"]),
            "orders": row["orders"],
            "total": row["total"],
        }
        for row in grouped
    ]
    total = {
        "orders": sum(row["orders"] for row in rows),
        "total": sum((row["total"] for row in rows), Decimal("0.00")),
    }
    return {"rows": rows, "total": total}
