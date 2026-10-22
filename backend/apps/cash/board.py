"""Lecturas de la pantalla de Caja (fase F3), siempre de una sola sede: en "todas" no se mezclan cajas.

El esperado sale de `expected_cash`, el mismo cálculo del arqueo. Cada bloque es una consulta agregada
o una lista: el número de consultas no crece con el número de movimientos.
"""

from decimal import Decimal

from django.db.models import Count, DecimalField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from apps.cash.choices import PaymentMethod
from apps.cash.models import CashMovement, CashSession, MovementKind
from apps.cash.selectors import current_session, expected_cash
from apps.receivables.models import Receivable
from apps.sales.selectors import day_bounds, local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

LAST_CLOSINGS = 5
STRIP = (MovementKind.SALE, MovementKind.RECEIVABLE_PAYMENT, MovementKind.EXPENSE, MovementKind.WITHDRAWAL)
_CASH = Q(payment_method=PaymentMethod.CASH)


def _money(condition: Q) -> Coalesce:
    return Coalesce(
        Sum("amount", filter=condition),
        Value(Decimal("0.00")),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )


def _strip(session: CashSession) -> dict:
    """Lo que entró y salió de la caja física por tipo, con cuántos movimientos, y el esperado."""
    aggregates = {}
    for kind in STRIP:
        condition = _CASH & Q(kind=kind)
        aggregates |= {f"{kind}_total": _money(condition), f"{kind}_count": Count("pk", filter=condition)}
    totals = CashMovement.objects.filter(session=session).aggregate(**aggregates)
    rows = {kind: {"total": totals[f"{kind}_total"], "count": totals[f"{kind}_count"]} for kind in STRIP}
    return {"by_kind": rows, "expected": expected_cash(session)}


def _movements(session: CashSession, kind: str | None) -> QuerySet[CashMovement]:
    """Todo lo que entra o sale de la caja física, del más reciente al más antiguo."""
    movements = CashMovement.objects.filter(session=session).filter(_CASH).select_related("created_by")
    if kind:
        movements = movements.filter(kind=kind)
    return movements.order_by("-created_at", "-pk")


def _other_media(membership: Membership, session: CashSession, scope: BranchScope) -> dict:
    """Lo que no entra a la caja física: ventas por otros medios y fiados nuevos de hoy en la sede."""
    others = CashMovement.objects.filter(session=session, kind=MovementKind.SALE).exclude(_CASH)
    transfers = others.aggregate(total=_money(Q()), count=Count("pk"))
    today = local_today(membership)
    start, end = day_bounds(membership.barbershop.timezone, today, today)
    new_debts = scope.apply(
        Receivable.objects.filter(order__isnull=False, created_at__gte=start, created_at__lt=end), "origin_branch"
    )
    credit = new_debts.aggregate(total=Coalesce(Sum("total"), Value(Decimal("0.00"))), count=Count("pk"))
    return {"transfers": transfers, "credit": credit}


def last_closings(scope: BranchScope) -> QuerySet[CashSession]:
    closed = scope.apply(CashSession.objects.filter(closed_at__isnull=False)).select_related("closed_by")
    return closed.order_by("-closed_at", "-pk")[:LAST_CLOSINGS]


def cash_register(membership: Membership, *, scope: BranchScope, kind: str | None = None) -> dict:
    """La caja de la sede del alcance: abierta con su franja, movimientos y otros medios, o sin abrir."""
    ensure_permission(membership, "caja.ver")
    scope.check(membership)
    if scope.is_all:
        return {"needs_branch": True}
    session = current_session(membership, scope=scope)
    data = {"needs_branch": False, "session": session, "closings": list(last_closings(scope))}
    if session is None:
        return data
    return {
        **data,
        **_strip(session),
        "movements": list(_movements(session, kind)),
        "other_media": _other_media(membership, session, scope),
    }
