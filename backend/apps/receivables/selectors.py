"""Lecturas de fiados. Ninguna escribe: los vencidos se calculan por fecha (defecto 25).

Los fiados son de su sede de origen (decisión 15 de docs/sedes.md): todo se lee por el alcance de sede.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db.models import Count, DecimalField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.clients.models import Client
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission

_ZERO = Decimal("0.00")


def _sum_balance(condition: Q | None = None) -> Coalesce:
    return Coalesce(
        Sum("balance", filter=condition), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2)
    )


def local_today(membership: Membership) -> date:
    return timezone.now().astimezone(ZoneInfo(membership.barbershop.timezone)).date()


def _open_balance(receivables: QuerySet[Receivable]) -> Decimal:
    """Deuda viva: pendientes y vencidos."""
    return receivables.filter(status__in=OPEN_STATUSES).aggregate(total=_sum_balance())["total"]


def client_balance(client: Client, *, branch: Branch) -> Decimal:
    """Deuda viva del cliente en una sede: la que cuenta para su límite de crédito allí."""
    return _open_balance(Receivable.objects.filter(client=client, origin_branch=branch))


def client_balance_in_scope(client: Client, *, scope: BranchScope) -> Decimal:
    """Deuda viva del cliente en las sedes del alcance, para su perfil."""
    return _open_balance(scope.apply(Receivable.objects.filter(client=client), "origin_branch"))


def _in_scope(membership: Membership, scope: BranchScope) -> QuerySet[Receivable]:
    scope.check(membership)
    return scope.apply(Receivable.objects.all(), "origin_branch")


def list_receivables(
    membership: Membership, *, scope: BranchScope, client: UUID | str | None = None, status: str | None = None
) -> QuerySet[Receivable]:
    ensure_permission(membership, "fiados.ver")
    receivables = _in_scope(membership, scope).select_related("client", "order")
    if client is not None:
        receivables = receivables.filter(client__public_id=client)
    if status:
        receivables = receivables.filter(status=status)
    return receivables.order_by("-created_at", "-pk")


def get_receivable(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> Receivable:
    """El fiado de otra sede no se encuentra: lanza `Receivable.DoesNotExist`."""
    ensure_permission(membership, "fiados.ver")
    return _in_scope(membership, scope).select_related("client", "order").get(public_id=public_id)


def receivables_summary(membership: Membership, *, scope: BranchScope) -> dict:
    """Regla 29: pendientes y vencidos (por fecha de vencimiento, no por el estado guardado)."""
    ensure_permission(membership, "fiados.ver")
    overdue = Q(due_date__isnull=False, due_date__lt=local_today(membership))
    return (
        _in_scope(membership, scope)
        .filter(status__in=OPEN_STATUSES, balance__gt=0)
        .aggregate(
            pending_count=Count("pk"),
            pending_balance=_sum_balance(),
            overdue_count=Count("pk", filter=overdue),
            overdue_balance=_sum_balance(overdue),
        )
    )
