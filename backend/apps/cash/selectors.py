"""Lecturas de caja. Los managers ya filtran por la barbería activa.

`expected_cash` es el único cálculo del efectivo esperado: lo usan el cierre y el
resumen, así que la pantalla y el arqueo nunca dan cifras distintas (defecto 23).
"""

from decimal import Decimal
from uuid import UUID

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.cash.choices import PaymentMethod
from apps.cash.models import CashMovement, CashSession, Direction
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission

_ZERO = Decimal("0.00")


def _sum(**filters) -> Coalesce:
    return Coalesce(
        Sum("amount", filter=Q(**filters)), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2)
    )


def expected_cash_total(sessions: list[CashSession]) -> Decimal:
    """Base + entradas en efectivo − salidas en efectivo, solo desde el libro de movimientos.

    De varias cajas a la vez en una sola consulta (el tablero en "todas" suma las de cada sede).
    """
    totals = CashMovement.objects.filter(session__in=sessions, payment_method=PaymentMethod.CASH).aggregate(
        cash_in=_sum(direction=Direction.IN), cash_out=_sum(direction=Direction.OUT)
    )
    opening = sum((session.opening_amount for session in sessions), Decimal("0.00"))
    return opening + totals["cash_in"] - totals["cash_out"]


def expected_cash(session: CashSession) -> Decimal:
    return expected_cash_total([session])


def open_session_for(branch: Branch) -> CashSession | None:
    """Caja abierta de la sede. sales y receivables la usan para registrar dinero; no exige permiso."""
    return CashSession.objects.filter(branch=branch, closed_at__isnull=True).first()


def current_session(membership: Membership, *, scope: BranchScope) -> CashSession | None:
    """La caja abierta de la sede del alcance. En "todas" no hay una sola: None.

    Decisión 14 de docs/sedes.md: una sede desactivada no tiene caja vigente.
    """
    ensure_permission(membership, "caja.ver")
    scope.check(membership)
    if scope.is_all:
        return None
    sessions = CashSession.objects.filter(branch__is_active=True, closed_at__isnull=True)
    return scope.apply(sessions).select_related("branch").first()


def session_summary(membership: Membership, session: UUID | str, *, scope: BranchScope) -> dict:
    """Totales por método y por tipo, y el efectivo esperado calculado igual que al cerrar.

    Solo una caja de la sede del alcance; la de otra sede no se encuentra.
    """
    ensure_permission(membership, "caja.ver")
    target = scope.readable(membership, CashSession.objects).select_related("branch").get(public_id=session)
    movements = CashMovement.objects.filter(session=target)

    by_method: dict[str, dict[str, Decimal]] = {}
    for row in movements.values("payment_method").annotate(
        total_in=_sum(direction=Direction.IN), total_out=_sum(direction=Direction.OUT)
    ):
        by_method[row["payment_method"]] = {
            "in": row["total_in"],
            "out": row["total_out"],
            "net": row["total_in"] - row["total_out"],
        }
    by_kind = {row["kind"]: row["total"] for row in movements.values("kind").annotate(total=Sum("amount"))}

    return {
        "session": target,
        "is_open": target.is_open,
        "opening_amount": target.opening_amount,
        "by_method": by_method,
        "by_kind": by_kind,
        "expected_cash": expected_cash(target),
        "counted_amount": target.counted_amount,
        "difference": target.difference,
    }
