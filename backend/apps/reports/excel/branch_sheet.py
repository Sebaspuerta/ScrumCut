"""Hoja "Resumen por sede" del reporte de negocio (fase S5 de docs/sedes.md): el comparativo y su Total."""

from apps.reports.excel.sheets import Sheet
from apps.reports.scope import Period
from apps.reports.selectors.branches import branch_comparison
from apps.tenancy.models import Membership

COLUMNS = (
    ("orders", "Comandas"),
    ("sales", "Ventas netas"),
    ("ticket", "Ticket promedio"),
    ("services", "Servicios"),
    ("products", "Productos"),
    ("expenses", "Gastos"),
    ("result", "Resultado operativo"),
    ("receivables_pending", "Fiados pendientes"),
    ("receivables_collected", "Fiados cobrados"),
    ("closings", "Cierres de caja"),
    ("closing_differences", "Diferencias de cierre"),
    ("stock_value", "Valor del stock"),
    ("units_in", "Unidades que entran"),
    ("units_out", "Unidades que salen"),
    ("transfers_in", "Traslados que entran"),
    ("transfers_out", "Traslados que salen"),
)
PRODUCTION_HEADER = ["Producción por barbero", "Barbero", "Comandas", "Ventas netas"]


def _branch_row(row: dict) -> list:
    status = "" if row["branch"] is None else ("Activa" if row["is_active"] else "Inactiva")
    return [row["name"], status, *(row[key] for key, _ in COLUMNS)]


def _production_rows(production: dict) -> list[list]:
    rows = [[], PRODUCTION_HEADER]
    rows += [[row["branch"], row["name"], row["orders"], row["total"]] for row in production["rows"]]
    rows.append(["Total", "", production["total"]["orders"], production["total"]["total"]])
    return rows


def branch_summary_sheet(membership: Membership, period: Period) -> Sheet:
    comparison = branch_comparison(membership, period.date_from, period.date_to, scope=period.scope)
    rows = [_branch_row(row) for row in comparison["branches"]]
    rows.append(_branch_row(comparison["total"]))
    rows += _production_rows(comparison["production"])
    return Sheet("Resumen por sede", ["Sede", "Estado", *(label for _, label in COLUMNS)], rows)
