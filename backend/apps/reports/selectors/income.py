"""Estado de resultados del período (regla 55), con los costos y comisiones copiados al cerrar."""

from datetime import date

from django.db.models import F

from apps.cash.models import CashMovement, MovementKind
from apps.reports.scope import closed_items, money_sum, resolve_period
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def income_statement(membership: Membership, date_from: date | None = None, date_to: date | None = None) -> dict:
    """Las comandas anuladas ya no cuentan como venta, así que sus devoluciones no se restan otra vez.

    Los retiros son dinero que sale de la caja hacia el dueño, no un gasto del negocio.
    """
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to)
    lines = closed_items(membership, period).aggregate(
        gross_sales=money_sum("line_total"),
        discounts=money_sum("line_discount"),
        product_cost=money_sum(F("unit_cost") * F("quantity")),
        consumables_cost=money_sum("consumables_cost"),
        commissions=money_sum("commission_amount"),
    )
    expenses = CashMovement.objects.filter(
        kind=MovementKind.EXPENSE, created_at__gte=period.start, created_at__lt=period.end
    ).aggregate(total=money_sum("amount"))["total"]
    net_sales = lines["gross_sales"] - lines["discounts"]
    gross_profit = net_sales - lines["product_cost"] - lines["consumables_cost"] - lines["commissions"]
    return {
        **lines,
        "net_sales": net_sales,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "operating_profit": gross_profit - expenses,
    }
