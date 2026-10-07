"""Lecturas de fiados. Ninguna escribe: los vencidos se calculan por fecha (defecto 25)."""

from datetime import date
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db.models import Count, DecimalField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.clients.models import Client
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

_ZERO = Decimal("0.00")


def _sum_balance(condition: Q | None = None) -> Coalesce:
    return Coalesce(
        Sum("balance", filter=condition), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2)
    )


def local_today(membership: Membership) -> date:
    return timezone.now().astimezone(ZoneInfo(membership.barbershop.timezone)).date()


def client_balance(client: Client) -> Decimal:
    """Deuda viva del cliente (pendientes y vencidos). Uso interno: sales y el perfil del cliente."""
    return Receivable.objects.filter(client=client, status__in=OPEN_STATUSES).aggregate(total=_sum_balance())["total"]


def list_receivables(
    membership: Membership, *, client: UUID | str | None = None, status: str | None = None
) -> QuerySet[Receivable]:
    ensure_permission(membership, "fiados.ver")
    receivables = Receivable.objects.select_related("client", "order")
    if client is not None:
        receivables = receivables.filter(client__public_id=client)
    if status:
        receivables = receivables.filter(status=status)
    return receivables.order_by("-created_at", "-pk")


def get_receivable(membership: Membership, public_id: UUID | str) -> Receivable:
    ensure_permission(membership, "fiados.ver")
    return Receivable.objects.select_related("client", "order").get(public_id=public_id)


def receivables_summary(membership: Membership) -> dict:
    """Regla 29: pendientes y vencidos (por fecha de vencimiento, no por el estado guardado)."""
    ensure_permission(membership, "fiados.ver")
    overdue = Q(due_date__isnull=False, due_date__lt=local_today(membership))
    return Receivable.objects.filter(status__in=OPEN_STATUSES, balance__gt=0).aggregate(
        pending_count=Count("pk"),
        pending_balance=_sum_balance(),
        overdue_count=Count("pk", filter=overdue),
        overdue_balance=_sum_balance(overdue),
    )
