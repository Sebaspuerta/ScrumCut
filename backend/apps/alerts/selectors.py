"""Lecturas de alertas. Ninguna escribe: generar y resolver alertas es solo de la tarea programada.

Van por el alcance de sede (fase S4b): la sede activa o, en "todas", las de todas las sedes.
"""

from django.core.paginator import Page, Paginator
from django.db.models import F, QuerySet

from apps.alerts.models import Alert
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _unresolved(membership: Membership, scope: BranchScope) -> QuerySet[Alert]:
    return scope.readable(membership, Alert.objects.filter(resolved_at__isnull=True))


def list_alerts(
    membership: Membership, *, scope: BranchScope, unread_only: bool = False, page: int = 1, page_size: int = 50
) -> Page:
    """No leídas primero; dentro de cada grupo, las más recientes arriba. Sin las resueltas."""
    ensure_permission(membership, "alertas.ver")
    alerts = _unresolved(membership, scope).select_related("product", "branch", "receivable__client", "read_by__user")
    if unread_only:
        alerts = alerts.filter(read_at__isnull=True)
    ordered = alerts.order_by(F("read_at").asc(nulls_first=True), "-created_at", "-pk")
    return Paginator(ordered, page_size).get_page(page)


def unread_count(membership: Membership, *, scope: BranchScope) -> int:
    ensure_permission(membership, "alertas.ver")
    return _unresolved(membership, scope).filter(read_at__isnull=True).count()
