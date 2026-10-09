"""Reportes de caja (regla 52). Leen lo guardado al cerrar y el libro de movimientos (defectos 18 a 20)."""

from datetime import date

from django.db.models import QuerySet

from apps.cash.models import CashMovement, CashSession
from apps.reports.scope import resolve_period
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def cash_closings(membership: Membership, date_from: date | None = None, date_to: date | None = None) -> QuerySet:
    """Cajas cerradas en el período con el esperado, el contado y la diferencia que se guardaron al cerrar."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to)
    return (
        CashSession.objects.filter(closed_at__gte=period.start, closed_at__lt=period.end)
        .values(
            "branch__name",
            "opened_at",
            "closed_at",
            "closed_by__email",
            "opening_amount",
            "expected_amount",
            "counted_amount",
            "difference",
        )
        .order_by("closed_at", "pk")
    )


def cash_movements(membership: Membership, date_from: date | None = None, date_to: date | None = None) -> QuerySet:
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to)
    return (
        CashMovement.objects.filter(created_at__gte=period.start, created_at__lt=period.end)
        .values(
            "created_at",
            "session__branch__name",
            "kind",
            "direction",
            "payment_method",
            "amount",
            "description",
            "created_by__email",
        )
        .order_by("created_at", "pk")
    )
