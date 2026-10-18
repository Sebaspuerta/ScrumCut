"""Comparativo entre sedes (fase S5 de docs/sedes.md): una fila por sede del alcance y su Total.

Cada métrica es una sola consulta agregada en la base y agrupada por sede (`values(...).annotate`):
el número de consultas no depende de cuántas sedes haya. El período va en la zona de la barbería
(la zona por sede sigue aplazada, decisión 7).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Abs, Coalesce

from apps.cash.models import CashMovement, CashSession, MovementKind
from apps.inventory.models import MovementType, StockLevel, StockMovement
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.reports.scope import NET_SALE, Period, closed_items, closed_orders, money_sum, resolve_period
from apps.reports.selectors.production import barber_production
from apps.sales.models import ItemType
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission

ZERO = Decimal("0.00")

# Lo que se suma en el Total. El ticket no: en el Total sale de las ventas y comandas del Total.
MONEY_METRICS = (
    "sales",
    "services",
    "products",
    "expenses",
    "result",
    "receivables_pending",
    "receivables_collected",
    "closing_differences",
    "stock_value",
)
COUNT_METRICS = ("orders", "closings", "units_in", "units_out", "transfers_in", "transfers_out")
# Lo que pasó en el período: una sede inactiva aparece si tiene alguno de estos, o un saldo vivo.
ACTIVITY_METRICS = ("orders", "expenses", "receivables_collected", "closings", "units_in", "units_out")
LIVE_BALANCES = ("receivables_pending", "stock_value")

Rows = dict[int, dict]


def _by_branch(rows, key: str) -> Rows:
    return {row.pop(key): row for row in rows}


def _sales(membership: Membership, period: Period) -> Rows:
    orders = closed_orders(membership, period).values("branch").annotate(orders=Count("pk"), sales=money_sum("total"))
    lines = (
        closed_items(membership, period)
        .values("order__branch")
        .annotate(
            services=money_sum(NET_SALE, Q(item_type=ItemType.SERVICE)),
            products=money_sum(NET_SALE, Q(item_type=ItemType.PRODUCT)),
        )
    )
    by_lines = _by_branch(lines, "order__branch")
    return {branch: row | by_lines.get(branch, {}) for branch, row in _by_branch(orders, "branch").items()}


def _cash_movements(period: Period) -> Rows:
    """Gastos (decisión 5) y abonos de fiados; un abono entra en la caja de su sede de origen (decisión 3)."""
    movements = CashMovement.objects.filter(created_at__gte=period.start, created_at__lt=period.end)
    rows = (
        period.scope.apply(movements, "session__branch")
        .values("session__branch")
        .annotate(
            expenses=money_sum("amount", Q(kind=MovementKind.EXPENSE)),
            receivables_collected=money_sum("amount", Q(kind=MovementKind.RECEIVABLE_PAYMENT)),
        )
    )
    return _by_branch(rows, "session__branch")


def _closings(period: Period) -> Rows:
    sessions = CashSession.objects.filter(closed_at__gte=period.start, closed_at__lt=period.end)
    rows = (
        period.scope.apply(sessions)
        .values("branch")
        .annotate(closings=Count("pk"), closing_differences=money_sum("difference"))
    )
    return _by_branch(rows, "branch")


def _pending_receivables(scope: BranchScope) -> Rows:
    """La deuda viva de hoy por sede de origen, como `receivables_summary`."""
    debts = Receivable.objects.filter(status__in=OPEN_STATUSES, balance__gt=0)
    rows = (
        scope.apply(debts, "origin_branch").values("origin_branch").annotate(receivables_pending=money_sum("balance"))
    )
    return _by_branch(rows, "origin_branch")


def _stock_value(scope: BranchScope) -> Rows:
    """Valor del stock de hoy: cantidad × costo de compra del producto, de productos no borrados."""
    levels = StockLevel.objects.filter(product__deleted_at__isnull=True)
    rows = (
        scope.apply(levels)
        .values("branch")
        .annotate(stock_value=money_sum(F("quantity") * F("product__purchase_cost")))
    )
    return _by_branch(rows, "branch")


def _transfers(period: Period) -> Rows:
    """Unidades trasladadas y traslados (por `transfer_id`). Solo cantidades: el antes y el después de
    los movimientos anteriores a S4b son de toda la barbería."""
    outgoing, incoming = Q(movement_type=MovementType.TRANSFER_OUT), Q(movement_type=MovementType.TRANSFER_IN)
    movements = StockMovement.objects.filter(
        transfer_id__isnull=False, created_at__gte=period.start, created_at__lt=period.end
    )
    rows = (
        period.scope.apply(movements)
        .values("branch")
        .annotate(
            units_in=Coalesce(Sum("quantity", filter=incoming), 0),
            units_out=Coalesce(Sum(Abs("quantity"), filter=outgoing), 0),
            transfers_in=Count("transfer_id", filter=incoming, distinct=True),
            transfers_out=Count("transfer_id", filter=outgoing, distinct=True),
        )
    )
    return _by_branch(rows, "branch")


def _empty_row() -> dict:
    return dict.fromkeys(MONEY_METRICS, ZERO) | dict.fromkeys(COUNT_METRICS, 0)


def _ticket(row: dict) -> Decimal:
    return (row["sales"] / row["orders"]).quantize(Decimal("1")) if row["orders"] else ZERO


def _finish(row: dict) -> dict:
    """Resultado operativo (ventas − gastos, no contable) y ticket promedio."""
    row["result"] = row["sales"] - row["expenses"]
    row["ticket"] = _ticket(row)
    return row


def _shows(branch: Branch, row: dict) -> bool:
    if branch.is_active:
        return True
    return any(row[metric] for metric in ACTIVITY_METRICS + LIVE_BALANCES)


def _rows(membership: Membership, period: Period) -> list[dict]:
    metrics = (
        _sales(membership, period),
        _cash_movements(period),
        _closings(period),
        _pending_receivables(period.scope),
        _stock_value(period.scope),
        _transfers(period),
    )
    rows = []
    for branch in period.scope.branches().order_by("name"):
        row = _empty_row()
        for by_branch in metrics:
            row |= by_branch.get(branch.pk, {})
        row = _finish(row)
        if _shows(branch, row):
            rows.append({"branch": branch.public_id, "name": branch.name, "is_active": branch.is_active, **row})
    return rows


def _total(rows: list[dict]) -> dict:
    """Exactamente la suma de las filas; el ticket sale de esas sumas."""
    total = _empty_row()
    for row in rows:
        for metric in MONEY_METRICS + COUNT_METRICS:
            total[metric] += row[metric]
    return {"branch": None, "name": "Total", "is_active": True, **total, "ticket": _ticket(total)}


def branch_comparison(
    membership: Membership, date_from: date | None = None, date_to: date | None = None, *, scope: BranchScope
) -> dict:
    """Ventas, gastos, resultado, fiados, caja, inventario y producción por sede del alcance, con su Total.

    El resultado es operativo (ventas − gastos de caja), no contable: no resta costos ni comisiones;
    eso es el estado de resultados. En modo "una", solo esa sede; "todas" exige además `sedes.ver`.
    Una sede inactiva sale, marcada, solo si tuvo movimiento en el período o conserva un saldo vivo.
    """
    ensure_permission(membership, "reportes.ver")
    if scope.is_all:
        ensure_permission(membership, "sedes.ver")
    period = resolve_period(membership, date_from, date_to, scope=scope)
    rows = _rows(membership, period)
    return {
        "date_from": period.date_from,
        "date_to": period.date_to,
        "branches": rows,
        "total": _total(rows),
        "production": barber_production(membership, period),
    }
