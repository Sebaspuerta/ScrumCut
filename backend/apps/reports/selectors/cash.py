"""Reportes de caja (regla 52). Leen lo guardado al cerrar y el libro de movimientos (defectos 18 a 20)."""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Q, QuerySet

from apps.cash.choices import PaymentMethod
from apps.cash.models import CashMovement, CashSession, Direction, MovementKind
from apps.cash.selectors import expected_cash
from apps.reports.scope import money_sum, resolve_period
from apps.sales.selectors import day_bounds, local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

# Cascada del cuadre (docs/diseno.md): lo que suma y lo que resta al efectivo, en el orden de la maqueta.
# "Otros" recoge ingresos manuales, devoluciones y ajustes para que la cascada siempre llegue al esperado.
_CASCADE = (
    ("Ventas en efectivo", "sales", 1),
    ("Abonos de fiados", "receivable_payments", 1),
    ("Otros ingresos", "other_in", 1),
    ("Gastos", "expenses", -1),
    ("Retiros", "withdrawals", -1),
    ("Otras salidas", "other_out", -1),
)
_OPTIONAL_STEPS = {"other_in", "other_out"}


def cash_closings(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> QuerySet:
    """Cajas cerradas en el período con el esperado, el contado y la diferencia que se guardaron al cerrar."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    sessions = CashSession.objects.filter(closed_at__gte=period.start, closed_at__lt=period.end)
    return (
        period.scope.apply(sessions)
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


def cash_movements(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> QuerySet:
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    movements = CashMovement.objects.filter(created_at__gte=period.start, created_at__lt=period.end)
    return (
        period.scope.apply(movements, "session__branch")
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


def _todays_sessions(scope: BranchScope, start: datetime, end: datetime) -> list[CashSession]:
    """Por sede del alcance: la caja abierta (aunque se abriera ayer) o, si no, la última que se cerró hoy."""
    sessions = scope.apply(CashSession.objects.all())
    open_sessions = list(sessions.filter(closed_at__isnull=True))
    open_branches = {session.branch_id for session in open_sessions}
    closed_today = (
        sessions.filter(closed_at__gte=start, closed_at__lt=end)
        .exclude(branch_id__in=open_branches)
        .order_by("branch_id", "-closed_at")
    )
    latest_closed = {}
    for session in closed_today:
        latest_closed.setdefault(session.branch_id, session)
    return open_sessions + list(latest_closed.values())


def _cash_totals(sessions: list[CashSession]) -> dict:
    kinds = MovementKind
    return CashMovement.objects.filter(session__in=sessions, payment_method=PaymentMethod.CASH).aggregate(
        sales=money_sum("amount", Q(kind=kinds.SALE)),
        receivable_payments=money_sum("amount", Q(kind=kinds.RECEIVABLE_PAYMENT)),
        other_in=money_sum("amount", Q(direction=Direction.IN, kind__in=(kinds.MANUAL_INCOME, kinds.ADJUSTMENT))),
        expenses=money_sum("amount", Q(kind=kinds.EXPENSE)),
        withdrawals=money_sum("amount", Q(kind=kinds.WITHDRAWAL)),
        other_out=money_sum("amount", Q(direction=Direction.OUT, kind__in=(kinds.REFUND, kinds.ADJUSTMENT))),
    )


def _step(label: str, kind: str, low: Decimal, high: Decimal) -> dict:
    return {"label": label, "kind": kind, "amount": high - low, "low": low, "high": high}


def _cascade(opening: Decimal, totals: dict, expected: Decimal, counted: Decimal | None) -> list[dict]:
    steps = [_step("Apertura", "total", Decimal("0"), opening)]
    running = opening
    for label, key, sign in _CASCADE:
        amount = totals[key]
        if key in _OPTIONAL_STEPS and not amount:
            continue
        after = running + sign * amount
        steps.append(_step(label, "up" if sign > 0 else "down", min(running, after), max(running, after)))
        running = after
    steps.append(_step("Esperado", "total", Decimal("0"), expected))
    if counted is not None:
        steps.append(_step("Contado", "counted", Decimal("0"), counted))
    return steps


def _with_bars(steps: list[dict]) -> list[dict]:
    """Posición de cada barra en porcentaje del punto más alto, como texto para un atributo data-."""
    peak = max((step["high"] for step in steps), default=Decimal("0")) or Decimal("1")
    for step in steps:
        step["bar"] = {"bottom": f"{step['low'] * 100 / peak:.2f}", "height": f"{step['amount'] * 100 / peak:.2f}"}
    return steps


def _total(values) -> Decimal:
    return sum(values, Decimal("0"))


def cash_flow_today(membership: Membership, *, scope: BranchScope) -> dict | None:
    """Cuadre de hoy: de la base al esperado (el mismo cálculo del arqueo) y, si ya cerró, el contado.

    En "todas", la suma de las cajas de hoy de cada sede; el contado y la diferencia solo cuando
    todas cerraron. El cuadre separado por sede llega con el comparativo (fase S5).
    """
    ensure_permission(membership, "reportes.ver")
    scope.check(membership)
    today = local_today(membership)
    sessions = _todays_sessions(scope, *day_bounds(membership.barbershop.timezone, today, today))
    if not sessions:
        return None
    expected = _total(expected_cash(session) for session in sessions)
    all_closed = all(not session.is_open for session in sessions)
    counted = _total(session.counted_amount for session in sessions) if all_closed else None
    opening = _total(session.opening_amount for session in sessions)
    return {
        "is_open": not all_closed,
        "opened_at": min(session.opened_at for session in sessions),
        "expected": expected,
        "difference": _total(session.difference for session in sessions) if all_closed else None,
        "steps": _with_bars(_cascade(opening, _cash_totals(sessions), expected, counted)),
    }


def latest_closings(membership: Membership, *, scope: BranchScope, limit: int = 5) -> list[dict]:
    """Los últimos cierres de las sedes del alcance con lo guardado al cerrar, por día local."""
    ensure_permission(membership, "reportes.ver")
    scope.check(membership)
    closed = scope.apply(CashSession.objects.filter(closed_at__isnull=False))
    sessions = closed.order_by("-closed_at")[:limit]
    tz = ZoneInfo(membership.barbershop.timezone)
    return [
        {
            "date": session.closed_at.astimezone(tz).date(),
            "expected": session.expected_amount,
            "counted": session.counted_amount,
            "difference": session.difference,
        }
        for session in sessions
    ]
