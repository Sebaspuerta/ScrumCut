"""Tablero (regla 53). Solo lee: generar alertas o marcar vencidos es de la tarea programada (defecto 26)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from apps.alerts.conditions import LOW_STOCK, OUT_OF_STOCK, alertable_levels
from apps.alerts.selectors import list_alerts, unread_count
from apps.cash.models import CashMovement, CashSession, MovementKind
from apps.cash.selectors import expected_cash, expected_cash_total
from apps.core.formatting import weekday_name
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.receivables.selectors import receivables_summary
from apps.reports.scope import money_sum
from apps.reports.selectors.calendar import month_bounds, sales_calendar
from apps.reports.selectors.cash import cash_flow_today, latest_closings
from apps.reports.selectors.sales import income_mix, sales_by_barber, sales_by_period, top_products
from apps.sales.models import EDITABLE_STATUSES, OrderStatus
from apps.sales.selectors import day_bounds, local_today, scoped_orders
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _income(start, end, scope: BranchScope) -> dict:
    """Cobros y abonos en todos los métodos, menos las devoluciones de comandas anuladas en esas fechas."""
    movements = scope.apply(CashMovement.objects.filter(created_at__gte=start, created_at__lt=end), "session__branch")
    income = movements.aggregate(
        sales=money_sum("amount", Q(kind=MovementKind.SALE)),
        receivable_payments=money_sum("amount", Q(kind=MovementKind.RECEIVABLE_PAYMENT)),
        refunds=money_sum("amount", Q(kind=MovementKind.REFUND)),
    )
    return {**income, "total": income["sales"] + income["receivable_payments"] - income["refunds"]}


def _open_sessions(scope: BranchScope):
    return scope.apply(CashSession.objects.filter(closed_at__isnull=True)).select_related("branch")


def _open_cash_sessions(scope: BranchScope) -> list[dict]:
    """El esperado sale de `expected_cash`, el mismo cálculo del arqueo, aunque la caja se abriera ayer (defecto 23)."""
    sessions = _open_sessions(scope).order_by("branch__name")
    return [
        {"branch": session.branch.name, "opened_at": session.opened_at, "expected_cash": expected_cash(session)}
        for session in sessions
    ]


def dashboard_summary(membership: Membership, *, scope: BranchScope) -> dict:
    ensure_permission(membership, "reportes.ver")
    scope.check(membership)
    today = local_today(membership)
    start, end = day_bounds(membership.barbershop.timezone, today, today)
    orders = scope.apply(scoped_orders(membership)).aggregate(
        closed_today=Count("pk", filter=Q(status=OrderStatus.CLOSED, closed_at__gte=start, closed_at__lt=end)),
        open=Count("pk", filter=Q(status__in=EDITABLE_STATUSES)),
    )
    return {
        "date": today,
        "income": _income(start, end, scope),
        "orders_closed_today": orders["closed_today"],
        "orders_open": orders["open"],
        "open_cash_sessions": _open_cash_sessions(scope),
        # Mismo criterio de las alertas "agotado" y "stock bajo". Cuenta existencias, no productos: en
        # "todas", un producto crítico en dos sedes suma 2 (una por producto × sede).
        "critical_stock": scope.apply(alertable_levels().filter(OUT_OF_STOCK | LOW_STOCK)).count(),
        "receivables": receivables_summary(membership, scope=scope),
        "unread_alerts": unread_count(membership, scope=scope),
    }


# ── Tablero ejecutivo (Main.dc.html) ─────────────────────────────────────────


def variation(current: Decimal | int | None, previous: Decimal | int | None) -> dict | None:
    """Cambio porcentual frente al período anterior del mismo largo; None si el anterior no tuvo datos."""
    if current is None or not previous:
        return None
    percent = (Decimal(current - previous) * 100 / previous).quantize(Decimal("0.1"))
    return {"percent": percent, "direction": "up" if percent >= 0 else "down"}


def _ticket(days: list[dict]) -> Decimal | None:
    orders = sum(day["orders"] for day in days)
    return (sum(day["total"] for day in days) / orders).quantize(Decimal("1")) if orders else None


# Lo de hoy se compara con el mismo día de la semana anterior (un sábado con otro sábado, Main.dc.html)
# cortado a la misma hora local: a las 2 a. m. un día que apenas empieza no se mide contra uno completo.
COMPARISON_DAYS = 7

Window = tuple[datetime, datetime]


def _so_far(tz: str, today: date) -> tuple[Window, Window]:
    """Hoy hasta ahora y el mismo día de la semana anterior hasta la misma hora local."""
    today_start, _ = day_bounds(tz, today, today)
    reference_day = today - timedelta(days=COMPARISON_DAYS)
    reference_start, _ = day_bounds(tz, reference_day, reference_day)
    elapsed = timezone.now() - today_start
    return (today_start, today_start + elapsed), (reference_start, reference_start + elapsed)


def _closed_in(window: Window) -> Q:
    return Q(status=OrderStatus.CLOSED, closed_at__gte=window[0], closed_at__lt=window[1])


def _orders_kpi(membership: Membership, scope: BranchScope, today_so_far: Window, reference: Window) -> dict:
    """Comandas cerradas hoy frente al mismo corte de la semana anterior, y las que siguen abiertas."""
    counts = scope.apply(scoped_orders(membership)).aggregate(
        today=Count("pk", filter=_closed_in(today_so_far)),
        reference=Count("pk", filter=_closed_in(reference)),
        open=Count("pk", filter=Q(status__in=EDITABLE_STATUSES)),
    )
    return {
        "value": counts["today"],
        "open": counts["open"],
        "variation": variation(counts["today"], counts["reference"]),
    }


def _income_kpi(scope: BranchScope, today_so_far: Window, reference: Window) -> dict:
    income = _income(*today_so_far, scope)["total"]
    return {"value": income, "variation": variation(income, _income(*reference, scope)["total"])}


def _cash_kpi(scope: BranchScope) -> dict | None:
    """Efectivo esperado en las cajas abiertas del alcance; en "todas", la suma de las sedes."""
    sessions = list(_open_sessions(scope))
    if not sessions:
        return None
    expected = expected_cash_total(sessions)
    return {"expected": expected, "opened_at": min(session.opened_at for session in sessions)}


def _receivables_kpi(membership: Membership, scope: BranchScope) -> dict:
    summary = receivables_summary(membership, scope=scope)
    debts = scope.apply(Receivable.objects.filter(status__in=OPEN_STATUSES, balance__gt=0), "origin_branch")
    return {**summary, "clients": debts.values("client").distinct().count()}


def _previous_range(date_from: date, date_to: date) -> tuple[date, date]:
    previous_to = date_from - timedelta(days=1)
    return previous_to - (date_to - date_from), previous_to


def _with_bar_widths(barbers: list[dict]) -> list[dict]:
    """Ancho de cada barra frente a quien más vendió, como texto para un atributo data-."""
    top = barbers[0]["sales"] if barbers else Decimal("0")
    for barber in barbers:
        barber["bar"] = f"{barber['sales'] * 100 / top:.2f}" if top else "0"
    return barbers


def _with_margins(products: list[dict]) -> list[dict]:
    for product in products:
        sales = product["sales"]
        product["margin"] = ((sales - product["cost"]) * 100 / sales).quantize(Decimal("1")) if sales else None
    return products


def _kpis(
    membership: Membership, scope: BranchScope, today: date, *, days: list[dict], previous_days: list[dict]
) -> dict:
    today_so_far, reference = _so_far(membership.barbershop.timezone, today)
    ticket = _ticket(days)
    return {
        "comparison": f"vs. {weekday_name(today)} anterior a esta hora",
        "income": _income_kpi(scope, today_so_far, reference),
        "orders": _orders_kpi(membership, scope, today_so_far, reference),
        "ticket": {"value": ticket, "variation": variation(ticket, _ticket(previous_days))},
        "cash": _cash_kpi(scope),
        "receivables": _receivables_kpi(membership, scope),
    }


def _period_end(last: date, today: date) -> date:
    """El mes en curso va hasta hoy; uno pasado, completo."""
    return min(last, today)


def _cash_today(membership: Membership, scope: BranchScope) -> dict:
    """En "todas" no se mezclan cajas: cada sede tiene la suya y el tablero pide elegir una."""
    if scope.is_all:
        return {"needs_branch": True, "flow": None}
    return {"needs_branch": False, "flow": cash_flow_today(membership, scope=scope)}


def executive_dashboard(membership: Membership, month: date, *, scope: BranchScope) -> dict:
    """El tablero del mes en la sede del alcance; en "todas", los indicadores suman las sedes (docs/sedes.md)."""
    ensure_permission(membership, "reportes.ver")
    scope.check(membership)
    today = local_today(membership)
    sales_month = sales_calendar(membership, month, scope=scope)
    date_from, last = month_bounds(month)
    date_to = _period_end(last, today)
    previous_days = sales_by_period(membership, *_previous_range(date_from, date_to), scope=scope)
    return {
        "date_from": date_from,
        "date_to": date_to,
        "scope_label": scope.branch.name if scope.branch else "Todas las sedes",
        "has_sales": sales_month["selling_days"] > 0,
        "kpis": _kpis(membership, scope, today, days=sales_month["days"], previous_days=previous_days),
        "calendar": sales_month,
        "cash": _cash_today(membership, scope),
        "barbers": _with_bar_widths(sales_by_barber(membership, date_from, date_to, scope=scope)),
        "mix": income_mix(membership, date_from, date_to, scope=scope),
        "products": _with_margins(top_products(membership, date_from, date_to, limit=5, scope=scope)),
        "closings": latest_closings(membership, scope=scope),
        "alerts": list(list_alerts(membership, scope=scope, unread_only=True, page_size=4)),
    }
