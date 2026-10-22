"""Ventas por día de un mes calendario (tablero, fase F2): la tabla calendario y los datos de las torres 3D.

Sale de `sales_by_period`, una sola consulta agregada por día local de la barbería, así que el número
de consultas no depende de cuántos días vendieron. Todo en Decimal; el JS solo recibe texto ya formateado.
"""

import calendar
from datetime import date
from decimal import Decimal

from apps.core.formatting import WEEKDAYS, day_label, format_cop
from apps.reports.selectors.sales import sales_by_period
from apps.sales.selectors import local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership

# Tono de cada día según lo que vendió frente al mejor día del mes: cinco niveles, del 0 al 4.
# Son los cortes de la maqueta (1.500, 2.000, 2.600 y 3.100 sobre un máximo de 3.460) como proporción.
LEVEL_STEPS = (Decimal("0.43"), Decimal("0.58"), Decimal("0.75"), Decimal("0.9"))
DAYS_IN_WEEK = 7
ZERO = Decimal("0.00")


def month_bounds(month: date) -> tuple[date, date]:
    """El primer y el último día del mes de `month`."""
    first = month.replace(day=1)
    return first, first.replace(day=calendar.monthrange(first.year, first.month)[1])


def sales_level(total: Decimal, peak: Decimal) -> int:
    return sum(total / peak >= step for step in LEVEL_STEPS) if peak else 0


def _cell(day: dict, today: date, peak: Decimal) -> dict:
    total, current = day["total"], day["day"]
    return {
        "date": current,
        "day": current.day,
        "total": total,
        "amount": format_cop(total),
        "label": day_label(current),
        "level": sales_level(total, peak),
        "ratio": float(total / peak) if peak else 0.0,
        "today": current == today,
        "future": current > today,
        "has_sales": bool(total),
    }


def _weeks(cells: list[dict]) -> list[dict]:
    """Semanas de lunes a domingo: casillas vacías (None) antes del día 1 y después del último."""
    padded = [None] * cells[0]["date"].weekday() + cells
    padded += [None] * (-len(padded) % DAYS_IN_WEEK)
    weeks = [padded[start : start + DAYS_IN_WEEK] for start in range(0, len(padded), DAYS_IN_WEEK)]
    return [{"days": week, "total": sum((cell["total"] for cell in week if cell), ZERO)} for week in weeks]


def _weekday_averages(cells: list[dict]) -> list[dict]:
    """Promedio de los días con ventas de cada día de la semana; None si ese día nunca vendió."""
    averages = []
    for weekday, name in enumerate(WEEKDAYS):
        totals = [cell["total"] for cell in cells if cell["date"].weekday() == weekday and cell["has_sales"]]
        averages.append({"day": name, "average": sum(totals) / len(totals) if totals else None})
    return averages


def _stats(cells: list[dict]) -> dict:
    selling = [cell for cell in cells if cell["has_sales"]]
    total = sum((cell["total"] for cell in cells), ZERO)
    return {
        "total": total,
        "selling_days": len(selling),
        "best": max(selling, key=lambda cell: cell["total"], default=None),
        "daily_average": total / len(selling) if selling else None,
        "last_sale": selling[-1] if selling else None,
    }


def _chart(weeks: list[dict]) -> list[list[dict | None]]:
    """Lo que dibujan las torres 3D, solo con texto y números que JSON acepta."""
    keys = ("day", "amount", "label", "level", "ratio", "today", "future", "has_sales")
    return [[{key: cell[key] for key in keys} if cell else None for cell in week["days"]] for week in weeks]


def sales_calendar(membership: Membership, month: date, *, scope: BranchScope) -> dict:
    """El mes completo, del día 1 al último, en la zona de la barbería y por el alcance de sede.

    En "todas", cada día es la suma de las sedes del alcance. Los días futuros van sin cifra.
    """
    first, last = month_bounds(month)
    days = sales_by_period(membership, first, last, scope=scope)
    peak, today = max(day["total"] for day in days), local_today(membership)
    cells = [_cell(day, today, peak) for day in days]
    weeks = _weeks(cells)
    return {
        "month": first,
        "days": days,
        "weeks": weeks,
        "weekdays": _weekday_averages(cells),
        "chart": _chart(weeks),
        **_stats(cells),
    }
