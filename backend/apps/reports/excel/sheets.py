"""Contenido de cada hoja del reporte de negocio (regla 55). Solo arma filas con los selectores de reportes."""

from collections.abc import Callable
from decimal import Decimal
from typing import NamedTuple

from apps.cash.choices import PaymentMethod
from apps.cash.models import Direction, MovementKind
from apps.receivables.selectors import receivables_summary
from apps.reports.scope import Period
from apps.reports.selectors import cash, income, receivables, sales
from apps.sales.models import ItemType
from apps.staff.models import CommissionType
from apps.tenancy.models import Membership


class Sheet(NamedTuple):
    title: str
    header: list[str]
    rows: list[list]


def _label(choices, value: str) -> str:
    return choices(value).label if value else ""


def sales_sheet(membership: Membership, period: Period) -> Sheet:
    header = ["Fecha", "Comanda", "Tipo", "Ítem", "Barbero", "Cantidad", "Precio unitario", "Total línea"]
    header += ["Descuento", "Venta neta", "Costo", "Comisión", "Margen"]
    rows = [
        [
            line["order__closed_at"],
            line["order__number"],
            _label(ItemType, line["item_type"]),
            line["name"],
            line["barber__display_name"],
            line["quantity"],
            line["unit_price"],
            line["line_total"],
            line["line_discount"],
            line["net"],
            line["cost"],
            line["commission_amount"],
            line["net"] - line["cost"] - line["commission_amount"],
        ]
        for line in sales.sale_lines(membership, period.date_from, period.date_to)
    ]
    return Sheet("Ventas", header, rows)


def commissions_sheet(membership: Membership, period: Period) -> Sheet:
    header = ["Fecha", "Comanda", "Barbero", "Servicio", "Cantidad", "Base", "Tipo", "Valor", "Comisión"]
    rows = [
        [
            line["order__closed_at"],
            line["order__number"],
            line["barber__display_name"],
            line["name"],
            line["quantity"],
            line["net"],
            _label(CommissionType, line["commission_type"]),
            line["commission_rate"],
            line["commission_amount"],
        ]
        for line in sales.commission_lines(membership, period.date_from, period.date_to)
    ]
    return Sheet("Comisiones", header, rows)


def receivables_sheet(membership: Membership, period: Period) -> Sheet:
    header = ["Cliente", "Fiados", "Saldo", "Vencido", "Vencimiento más antiguo"]
    rows = [
        [
            row["client__full_name"],
            row["receivables"],
            row["pending_balance"],
            row["overdue_balance"],
            row["oldest_due"],
        ]
        for row in receivables.receivables_report(membership)["by_client"]
    ]
    return Sheet("Fiados", header, rows)


def movements_sheet(membership: Membership, period: Period) -> Sheet:
    header = ["Fecha", "Sede", "Tipo", "Sentido", "Método", "Monto", "Descripción", "Registró"]
    rows = [
        [
            row["created_at"],
            row["session__branch__name"],
            _label(MovementKind, row["kind"]),
            _label(Direction, row["direction"]),
            _label(PaymentMethod, row["payment_method"]),
            row["amount"],
            row["description"],
            row["created_by__email"],
        ]
        for row in cash.cash_movements(membership, period.date_from, period.date_to)
    ]
    return Sheet("Movimientos de caja", header, rows)


def closings_sheet(membership: Membership, period: Period) -> Sheet:
    header = ["Sede", "Abierta", "Cerrada", "Cerró", "Base", "Esperado", "Contado", "Diferencia"]
    rows = [
        [
            row["branch__name"],
            row["opened_at"],
            row["closed_at"],
            row["closed_by__email"],
            row["opening_amount"],
            row["expected_amount"],
            row["counted_amount"],
            row["difference"],
        ]
        for row in cash.cash_closings(membership, period.date_from, period.date_to)
    ]
    return Sheet("Cierres de caja", header, rows)


_STATEMENT_CONCEPTS = [
    ("gross_sales", "Ventas brutas"),
    ("discounts", "Descuentos"),
    ("net_sales", "Ventas netas"),
    ("product_cost", "Costo de productos vendidos"),
    ("consumables_cost", "Costo de insumos"),
    ("commissions", "Comisiones"),
    ("gross_profit", "Utilidad bruta"),
    ("expenses", "Gastos de caja"),
    ("operating_profit", "Utilidad operativa"),
]


def statement_sheet(membership: Membership, period: Period) -> Sheet:
    statement = income.income_statement(membership, period.date_from, period.date_to)
    return Sheet(
        "Estado de resultados", ["Concepto", "Valor"], [[label, statement[key]] for key, label in _STATEMENT_CONCEPTS]
    )


def _indicators(membership: Membership, days: list[dict]) -> list[list]:
    orders = sum(day["orders"] for day in days)
    net_sales = sum((day["total"] for day in days), Decimal("0"))
    debts = receivables_summary(membership)
    return [
        ["Comandas cerradas", orders],
        ["Ventas netas", net_sales],
        ["Ticket promedio", round(net_sales / orders, 2) if orders else Decimal("0")],
        ["Fiados pendientes", debts["pending_balance"]],
        ["Fiados vencidos", debts["overdue_balance"]],
    ]


def overview_sheet(membership: Membership, period: Period) -> Sheet:
    days = sales.sales_by_period(membership, period.date_from, period.date_to)
    rows = _indicators(membership, days)
    rows += [[], ["Ventas por día", "Comandas", "Ventas netas"]]
    rows += [[day["day"], day["orders"], day["total"]] for day in days]
    rows += [[], ["Ventas por barbero", "Ventas netas", "Comisión"]]
    rows += [
        [row["name"], row["sales"], row["commission"]]
        for row in sales.sales_by_barber(membership, period.date_from, period.date_to)
    ]
    rows += [[], ["Productos más vendidos", "Cantidad", "Venta neta"]]
    rows += [
        [row["name"], row["quantity"], row["sales"]]
        for row in sales.top_products(membership, period.date_from, period.date_to)
    ]
    return Sheet("Panorama", ["Indicador", "Valor"], rows)


SHEETS: list[Callable[[Membership, Period], Sheet]] = [
    overview_sheet,
    sales_sheet,
    commissions_sheet,
    receivables_sheet,
    movements_sheet,
    closings_sheet,
    statement_sheet,
]
