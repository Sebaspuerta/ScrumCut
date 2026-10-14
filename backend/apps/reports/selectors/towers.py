"""Torres 3D de ventas por día (docs/diseno.md): semanas de lunes a domingo, listas para que el JS solo dibuje."""

from datetime import date, timedelta
from decimal import Decimal

from apps.core.formatting import WEEKDAYS, day_label, format_cop

# Tono de cada torre según lo que vendió frente al mejor día. Son los cortes de la maqueta
# (1.500, 2.000, 2.600 y 3.100 sobre un máximo de 3.460) expresados como proporción.
LEVEL_STEPS = (Decimal("0.43"), Decimal("0.58"), Decimal("0.75"), Decimal("0.9"))


def _level(ratio: Decimal) -> int:
    return sum(ratio >= step for step in LEVEL_STEPS)


def _cell(day: dict | None, current: date, today: date, peak: Decimal) -> dict:
    if day is None:  # fuera del período: piso sin torre
        return {"date": current.isoformat(), "in_period": False}
    ratio = day["total"] / peak if peak else Decimal("0")
    return {
        "date": current.isoformat(),
        "in_period": True,
        "label": day_label(current) + (" · hoy" if current == today else ""),
        "amount": format_cop(day["total"]),
        "ratio": float(ratio),
        "level": _level(ratio),
        "closed": not day["total"],
        "today": current == today,
    }


def _weekday_averages(days: list[dict]) -> list[dict]:
    """Promedio de los días con ventas de cada día de la semana; None si nunca vendió (se muestra Cerrado)."""
    averages = []
    for weekday, name in enumerate(WEEKDAYS):
        totals = [day["total"] for day in days if day["day"].weekday() == weekday and day["total"]]
        averages.append({"day": name, "average": sum(totals) / len(totals) if totals else None})
    return averages


def build_towers(days: list[dict], today: date) -> dict:
    """`days` es la salida de `sales_by_period`: un día por fila, con 0 los días sin ventas."""
    by_date = {day["day"]: day for day in days}
    first, last = days[0]["day"], days[-1]["day"]
    start = first - timedelta(days=first.weekday())
    span = (last - start).days + 7 - last.weekday()
    peak = max(day["total"] for day in days)
    cells = [
        _cell(by_date.get(current), current, today, peak)
        for current in (start + timedelta(days=offset) for offset in range(span))
    ]
    selling = [day for day in days if day["total"]]
    total = sum((day["total"] for day in days), Decimal("0"))
    best = max(selling, key=lambda day: day["total"], default=None)
    in_period = [cell for cell in cells if cell["in_period"]]
    return {
        "weeks": [cells[index : index + 7] for index in range(0, len(cells), 7)],
        # Lectura inicial: hoy si está en el período; si no, el último día.
        "focus": next((cell for cell in in_period if cell["today"]), in_period[-1]),
        "weekdays": _weekday_averages(days),
        "total": total,
        "selling_days": len(selling),
        "best": best and {"day": best["day"], "total": best["total"]},
        "daily_average": total / len(selling) if selling else None,
    }
