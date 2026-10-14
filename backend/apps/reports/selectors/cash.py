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
from apps.tenancy.models import Branch, Membership
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


def _in_branch(queryset: QuerySet, lookup: str, branch: Branch | None) -> QuerySet:
    return queryset.filter(**{lookup: branch}) if branch else queryset


def cash_closings(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, branch: Branch | None = None
) -> QuerySet:
    """Cajas cerradas en el período con el esperado, el contado y la diferencia que se guardaron al cerrar."""
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to)
    sessions = CashSession.objects.filter(closed_at__gte=period.start, closed_at__lt=period.end)
    return (
        _in_branch(sessions, "branch", branch)
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
    membership: Membership, date_from: date | None = None, date_to: date | None = None, branch: Branch | None = None
) -> QuerySet:
    ensure_permission(membership, "reportes.ver")
    period = resolve_period(membership, date_from, date_to)
    movements = CashMovement.objects.filter(created_at__gte=period.start, created_at__lt=period.end)
    return (
        _in_branch(movements, "session__branch", branch)
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


def _todays_session(branch: Branch, start: datetime, end: datetime) -> CashSession | None:
    """La caja abierta de la sede (aunque se abriera ayer) o, si no, la que se cerró hoy."""
    sessions = CashSession.objects.filter(branch=branch)
    return (
        sessions.filter(closed_at__isnull=True).first()
        or sessions.filter(closed_at__gte=start, closed_at__lt=end).order_by("-closed_at").first()
    )


def _cash_totals(session: CashSession) -> dict:
    kinds = MovementKind
    return CashMovement.objects.filter(session=session, payment_method=PaymentMethod.CASH).aggregate(
        sales=money_sum("amount", Q(kind=kinds.SALE)),
        receivable_payments=money_sum("amount", Q(kind=kinds.RECEIVABLE_PAYMENT)),
        other_in=money_sum("amount", Q(direction=Direction.IN, kind__in=(kinds.MANUAL_INCOME, kinds.ADJUSTMENT))),
        expenses=money_sum("amount", Q(kind=kinds.EXPENSE)),
        withdrawals=money_sum("amount", Q(kind=kinds.WITHDRAWAL)),
        other_out=money_sum("amount", Q(direction=Direction.OUT, kind__in=(kinds.REFUND, kinds.ADJUSTMENT))),
    )


def _step(label: str, kind: str, low: Decimal, high: Decimal) -> dict:
    return {"label": label, "kind": kind, "amount": high - low, "low": low, "high": high}


def _cascade(session: CashSession, totals: dict, expected: Decimal) -> list[dict]:
    steps = [_step("Apertura", "total", Decimal("0"), session.opening_amount)]
    running = session.opening_amount
    for label, key, sign in _CASCADE:
        amount = totals[key]
        if key in _OPTIONAL_STEPS and not amount:
            continue
        after = running + sign * amount
        steps.append(_step(label, "up" if sign > 0 else "down", min(running, after), max(running, after)))
        running = after
    steps.append(_step("Esperado", "total", Decimal("0"), expected))
    if session.counted_amount is not None:
        steps.append(_step("Contado", "counted", Decimal("0"), session.counted_amount))
    return steps


def _with_bars(steps: list[dict]) -> list[dict]:
    """Posición de cada barra en porcentaje del punto más alto, como texto para un atributo data-."""
    peak = max((step["high"] for step in steps), default=Decimal("0")) or Decimal("1")
    for step in steps:
        step["bar"] = {"bottom": f"{step['low'] * 100 / peak:.2f}", "height": f"{step['amount'] * 100 / peak:.2f}"}
    return steps


def cash_flow_today(membership: Membership, branch: Branch) -> dict | None:
    """Cuadre de la caja de hoy: de la base al esperado (el mismo cálculo del arqueo) y, si ya cerró, el contado."""
    ensure_permission(membership, "reportes.ver")
    today = local_today(membership)
    session = _todays_session(branch, *day_bounds(membership.barbershop.timezone, today, today))
    if session is None:
        return None
    expected = expected_cash(session)
    return {
        "is_open": session.is_open,
        "opened_at": session.opened_at,
        "expected": expected,
        "difference": session.difference,
        "steps": _with_bars(_cascade(session, _cash_totals(session), expected)),
    }


def latest_closings(membership: Membership, branch: Branch, limit: int = 5) -> list[dict]:
    """Los últimos cierres de la sede con lo guardado al cerrar, por día local."""
    ensure_permission(membership, "reportes.ver")
    sessions = CashSession.objects.filter(branch=branch, closed_at__isnull=False).order_by("-closed_at")[:limit]
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
