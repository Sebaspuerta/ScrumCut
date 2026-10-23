"""Lecturas de la pantalla de Fiados (fase F4): cartera, antigüedad, pestañas y lista por urgencia.

Por las sedes del alcance, según la sede de origen de cada fiado (decisión 3 de docs/sedes.md). La franja,
la antigüedad y los conteos de las pestañas salen de una sola consulta agregada; lo cobrado en el mes, de
otra. El vencimiento se calcula por fecha, no por el estado guardado (regla 29).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.core.paginator import Page, Paginator
from django.db.models import Count, DecimalField, F, Prefetch, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from apps.receivables.models import OPEN_STATUSES, Receivable, ReceivablePayment, ReceivableStatus
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

PENDING, OVERDUE, PAID = "pendientes", "vencidos", "pagados"
PAGE_SIZE = 50
DUE_SOON_DAYS = 7
AGING = (
    ("current", "Al día"),
    ("d1_15", "Vencido 1 a 15 días"),
    ("d16_30", "Vencido 16 a 30 días"),
    ("d30", "Vencido más de 30 días"),
)
_ZERO = Value(Decimal("0.00"))


@dataclass(frozen=True)
class ReceivableFilter:
    tab: str = PENDING
    search: str = ""


def _money(condition: Q) -> Coalesce:
    return Coalesce(Sum("balance", filter=condition), _ZERO, output_field=DecimalField(max_digits=14, decimal_places=2))


def _conditions(today: date, month_start: datetime) -> dict[str, Q]:
    alive = Q(status__in=OPEN_STATUSES, balance__gt=0)
    overdue = alive & Q(due_date__lt=today)
    return {
        PENDING: alive,
        OVERDUE: overdue,
        PAID: Q(status=ReceivableStatus.PAID, updated_at__gte=month_start),
        "due_soon": alive & Q(due_date__gte=today, due_date__lte=today + timedelta(days=DUE_SOON_DAYS)),
        "current": alive & (Q(due_date__isnull=True) | Q(due_date__gte=today)),
        "d1_15": overdue & Q(due_date__gte=today - timedelta(days=15)),
        "d16_30": overdue & Q(due_date__lt=today - timedelta(days=15), due_date__gte=today - timedelta(days=30)),
        "d30": overdue & Q(due_date__lt=today - timedelta(days=30)),
    }


def _in_scope(membership: Membership, scope: BranchScope) -> QuerySet[Receivable]:
    ensure_permission(membership, "fiados.ver")
    return scope.readable(membership, Receivable.objects.all(), "origin_branch")


def portfolio(membership: Membership, *, scope: BranchScope, today: date, month_start: datetime) -> dict:
    """Por cobrar, vencido, vence en 7 días, antigüedad en cuatro tramos y conteo de cada pestaña."""
    conditions = _conditions(today, month_start)
    aggregates = {f"{key}_total": _money(q) for key, q in conditions.items() if key != PAID}
    aggregates |= {f"{key}_count": Count("pk", filter=q) for key, q in conditions.items()}
    aggregates |= {
        f"{key}_clients": Count("client", distinct=True, filter=conditions[key])
        for key in (PENDING, OVERDUE, "due_soon")
    }
    return _in_scope(membership, scope).aggregate(**aggregates)


def collected_this_month(membership: Membership, *, scope: BranchScope, month_start: datetime) -> dict:
    payments = scope.apply(ReceivablePayment.objects.filter(created_at__gte=month_start), "receivable__origin_branch")
    return payments.aggregate(total=Coalesce(Sum("amount"), _ZERO), count=Count("pk"))


def aging(data: dict) -> list[dict]:
    """Los cuatro tramos con su parte del total por cobrar; suman exactamente el total."""
    total = data[f"{PENDING}_total"]
    return [
        {
            "key": key,
            "label": label,
            "amount": data[f"{key}_total"],
            "percent": round(data[f"{key}_total"] * 100 / total) if total else 0,
        }
        for key, label in AGING
    ]


def receivable_rows(
    membership: Membership, *, scope: BranchScope, filters: ReceivableFilter, today: date, month_start: datetime
) -> Page:
    """La pestaña elegida; los vivos por urgencia (los más vencidos primero) y los pagados, los más recientes."""
    receivables = _in_scope(membership, scope).filter(_conditions(today, month_start)[filters.tab])
    if filters.search.strip():
        receivables = receivables.filter(client__full_name__icontains=filters.search.strip())
    if filters.tab == PAID:
        ordered = receivables.order_by("-updated_at")
    else:
        ordered = receivables.order_by(F("due_date").asc(nulls_last=True), "created_at", "pk")
    return Paginator(ordered.select_related("client", "order", "origin_branch"), PAGE_SIZE).get_page(1)


def receivable_detail(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> Receivable:
    """El fiado elegido con sus abonos y quién los recibió. Lanza `Receivable.DoesNotExist`."""
    payments = ReceivablePayment.objects.select_related("received_by").order_by("-created_at")
    return (
        _in_scope(membership, scope)
        .select_related("client", "order", "origin_branch")
        .prefetch_related(Prefetch("payments", queryset=payments))
        .get(public_id=public_id)
    )


def due_status(receivable: Receivable, today: date) -> dict:
    """El estado en texto, sin rojos: "▾ Vencido hace N días", "Vence en N días", "Vence hoy" o "Al día"."""
    if receivable.status == ReceivableStatus.PAID:
        return {"text": "Pagado", "tone": "done"}
    if receivable.due_date is None:
        return {"text": "Al día", "tone": "ok"}
    days = (receivable.due_date - today).days
    if days < 0:
        return {"text": f"▾ Vencido hace {-days} día{'s' if days != -1 else ''}", "tone": "overdue"}
    if days == 0:
        return {"text": "Vence hoy", "tone": "soon"}
    if days <= DUE_SOON_DAYS:
        return {"text": f"Vence en {days} día{'s' if days != 1 else ''}", "tone": "soon"}
    return {"text": "Al día", "tone": "ok"}
