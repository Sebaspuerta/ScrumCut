"""El tablero de la app de React: el mismo `executive_dashboard` de la pantalla en plantillas, en JSON.

No calcula nada nuevo: arma el mes con `MonthFilterForm` (?mes=AAAA-MM, validado en el servidor) y
reacomoda lo que devuelven los selectores de reportes, que ya validan permiso y alcance de sede.
"""

from datetime import date
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.api.notifications import alert_item
from apps.cash.board import stale_session
from apps.core.formatting import month_label
from apps.core.navigation import unread_alerts
from apps.reports.forms import MONTH_FORMAT, MonthFilterForm
from apps.reports.selectors.dashboard import executive_dashboard
from apps.sales.selectors import local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership

TREND_DAYS = 7  # la mini tendencia de los indicadores: los últimos días del período


def _months(membership: Membership, requested: str | None) -> tuple[date, str | None, str | None]:
    """El mes pedido (o el actual si no vale) y los meses vecinos que se pueden elegir."""
    since = timezone.localdate(membership.barbershop.created_at, ZoneInfo(membership.barbershop.timezone))
    form = MonthFilterForm({"mes": requested or ""}, today=local_today(membership), since=since)
    values = [choice["value"] for choice in form.choices()]  # del más reciente al más antiguo
    chosen = form.month().strftime(MONTH_FORMAT)
    position = values.index(chosen)
    newer = values[position - 1] if position > 0 else None
    older = values[position + 1] if position + 1 < len(values) else None
    return form.month(), older, newer


def _cell(cell: dict, orders: dict[date, int]) -> dict:
    count = orders.get(cell["date"], 0)
    keys = ("date", "day", "total", "level", "ratio", "today", "future", "has_sales")
    return {**{key: cell[key] for key in keys}, "orders": count, "ticket": cell["total"] / count if count else None}


def _calendar(calendar: dict) -> dict:
    orders = {day["day"]: day["orders"] for day in calendar["days"]}
    best, last = calendar["best"], calendar["last_sale"]
    return {
        "weeks": [
            # Solo los días del mes: las casillas vacías de la primera y la última semana las pone el cliente.
            {"days": [_cell(cell, orders) for cell in week["days"] if cell], "total": week["total"]}
            for week in calendar["weeks"]
        ],
        "total": calendar["total"],
        "selling_days": calendar["selling_days"],
        "daily_average": calendar["daily_average"],
        "best": {"date": best["date"], "total": best["total"]} if best else None,
        "last_sale": {"date": last["date"], "total": last["total"]} if last else None,
    }


def _trend(days: list[dict], until: date) -> dict:
    recent = [day for day in days if day["day"] <= until][-TREND_DAYS:]
    return {
        "income": [day["total"] for day in recent],
        "orders": [day["orders"] for day in recent],
        "ticket": [day["total"] / day["orders"] if day["orders"] else 0 for day in recent],
    }


def _cash(cash: dict) -> dict:
    flow = cash["flow"]
    if flow is not None:
        steps = [{key: step[key] for key in ("label", "kind", "amount")} for step in flow["steps"]]
        flow = {**{key: flow[key] for key in ("is_open", "opened_at", "expected", "difference")}, "steps": steps}
    return {"needs_branch": cash["needs_branch"], "flow": flow}


def _lists(data: dict) -> dict:
    return {
        "barbers": [
            {key: barber[key] for key in ("name", "orders", "services", "sales", "commission")}
            for barber in data["barbers"]
        ],
        "products": [
            {
                "name": product["name"],
                "units": product["quantity"],
                "sales": product["sales"],
                "margin": product["margin"],
            }
            for product in data["products"]
        ],
        "closings": data["closings"],
        "alerts": [alert_item(alert) for alert in data["alerts"]],
    }


def dashboard(membership: Membership, *, scope: BranchScope, requested_month: str | None) -> dict:
    """El tablero del mes en el alcance de la sesión; en "todas", la caja pide elegir una sede."""
    month, older, newer = _months(membership, requested_month)
    data = executive_dashboard(membership, month, scope=scope)
    return {
        "month": month.strftime(MONTH_FORMAT),
        "month_label": month_label(month),
        "previous_month": older,
        "next_month": newer,
        "today": local_today(membership),
        "timezone": membership.barbershop.timezone,
        "scope_label": data["scope_label"],
        "stale_cash": stale_session(membership, scope=scope) is not None,
        "kpis": data["kpis"],
        "trend": _trend(data["calendar"]["days"], data["date_to"]),
        "calendar": _calendar(data["calendar"]),
        "cash": _cash(data["cash"]),
        "unread_alerts": unread_alerts(membership, scope),
        **_lists(data),
    }
