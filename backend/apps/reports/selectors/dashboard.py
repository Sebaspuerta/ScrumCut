"""Tablero del día (regla 53). Solo lee: generar alertas o marcar vencidos es de la tarea programada (defecto 26)."""

from django.db.models import Count, Q

from apps.alerts.conditions import LOW_STOCK, OUT_OF_STOCK, alertable_products
from apps.alerts.selectors import unread_count
from apps.cash.models import CashMovement, CashSession, MovementKind
from apps.cash.selectors import expected_cash
from apps.receivables.selectors import receivables_summary
from apps.reports.scope import money_sum
from apps.sales.models import EDITABLE_STATUSES, OrderStatus
from apps.sales.selectors import day_bounds, local_today, scoped_orders
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _income(start, end) -> dict:
    """Cobros y abonos de hoy en todos los métodos, menos las devoluciones de comandas anuladas hoy."""
    return CashMovement.objects.filter(created_at__gte=start, created_at__lt=end).aggregate(
        sales=money_sum("amount", Q(kind=MovementKind.SALE)),
        receivable_payments=money_sum("amount", Q(kind=MovementKind.RECEIVABLE_PAYMENT)),
        refunds=money_sum("amount", Q(kind=MovementKind.REFUND)),
    )


def _open_cash_sessions() -> list[dict]:
    """El esperado sale de `expected_cash`, el mismo cálculo del arqueo, aunque la caja se abriera ayer (defecto 23)."""
    sessions = CashSession.objects.filter(closed_at__isnull=True).select_related("branch").order_by("branch__name")
    return [
        {"branch": session.branch.name, "opened_at": session.opened_at, "expected_cash": expected_cash(session)}
        for session in sessions
    ]


def dashboard_summary(membership: Membership) -> dict:
    ensure_permission(membership, "reportes.ver")
    today = local_today(membership)
    start, end = day_bounds(membership.barbershop.timezone, today, today)
    income = _income(start, end)
    orders = scoped_orders(membership).aggregate(
        closed_today=Count("pk", filter=Q(status=OrderStatus.CLOSED, closed_at__gte=start, closed_at__lt=end)),
        open=Count("pk", filter=Q(status__in=EDITABLE_STATUSES)),
    )
    return {
        "date": today,
        "income": {**income, "total": income["sales"] + income["receivable_payments"] - income["refunds"]},
        "orders_closed_today": orders["closed_today"],
        "orders_open": orders["open"],
        "open_cash_sessions": _open_cash_sessions(),
        # Mismo criterio de las alertas "agotado" y "stock bajo".
        "critical_stock": alertable_products().filter(OUT_OF_STOCK | LOW_STOCK).count(),
        "receivables": receivables_summary(membership),
        "unread_alerts": unread_count(membership),
    }
