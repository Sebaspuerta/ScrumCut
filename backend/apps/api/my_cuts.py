"""«Mis cortes» en la app de React: lo que lee `sales.selectors.my_cuts`, en JSON.

No calcula nada: la producción y la comisión son las copiadas en cada línea al cerrar la comanda. El barbero
sale de la sesión; ninguna petición lo elige.
"""

from datetime import date

from apps.sales.models import Order
from apps.sales.selectors import barber_display_name, item_display_name, my_cuts
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership


def _period(totals: dict) -> dict:
    return {
        "orders": totals["orders_count"],
        "cuts": totals["services_count"],
        "production": totals["sales_total"],
        "commission": totals["commission_total"],
    }


def _row(order: Order) -> dict:
    """Solo lo del barbero en la comanda: sus líneas, su venta y su comisión, nunca las de otro barbero."""
    return {
        "id": order.public_id,
        "number": order.number,
        "closed_at": order.closed_at,
        "items": ", ".join(item_display_name(line) for line in order.my_lines),
        "cuts": order.my_services,
        "production": order.my_sales,
        "commission": order.my_commission,
    }


def my_cuts_page(membership: Membership, *, scope: BranchScope, day: date | None, page: int) -> dict:
    data = my_cuts(membership, scope=scope, day=day, page=page)
    orders = data["orders"]
    return {
        "barber": barber_display_name(data["barber"]),
        "day": data["day"],
        "today": _period(data["today"]),
        "month": _period(data["month"]),
        "count": orders.paginator.count,
        "page": orders.number,
        "pages": orders.paginator.num_pages,
        "page_size": orders.paginator.per_page,
        "results": [_row(order) for order in orders],
    }
