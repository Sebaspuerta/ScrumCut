"""Reporte de fiados: la deuda viva de hoy, por cliente, en una sola consulta (defecto 27)."""

from django.db.models import Count, Min, Q

from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.receivables.selectors import receivables_summary
from apps.reports.scope import money_sum
from apps.sales.selectors import local_today
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def receivables_report(membership: Membership) -> dict:
    """Vencido por fecha de vencimiento, no por el estado guardado (regla 29)."""
    ensure_permission(membership, "reportes.ver")
    overdue = Q(due_date__lt=local_today(membership))
    by_client = (
        Receivable.objects.filter(status__in=OPEN_STATUSES, balance__gt=0)
        .values("client__public_id", "client__full_name")
        .annotate(
            receivables=Count("pk"),
            pending_balance=money_sum("balance"),
            overdue_balance=money_sum("balance", overdue),
            oldest_due=Min("due_date"),
        )
        .order_by("-pending_balance", "client__full_name")
    )
    return {"summary": receivables_summary(membership), "by_client": list(by_client)}
