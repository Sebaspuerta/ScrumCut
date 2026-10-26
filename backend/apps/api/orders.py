"""Comandas en la app de React: lo mismo que leen las pantallas de Django (`sales.board`, `sales.order_page`), en JSON.

No calcula nada nuevo: los totales, los saldos, el cupo de fiado y qué acciones permite el rol los decide el
backend. El celular del cliente sale enmascarado.
"""

from datetime import date
from uuid import UUID

from apps.cash.board import stale_session
from apps.cash.selectors import payment_methods
from apps.clients.models import Client
from apps.core.formatting import mask_phone
from apps.sales.board import CLOSED_TODAY, TABS, BoardFilter, board_orders, board_row, closed_today_summary, tab_counts
from apps.sales.forms import MAX_LINE_QUANTITY
from apps.sales.models import EDITABLE_STATUSES, Order, OrderStatus
from apps.sales.order_page import catalog_for_branch, order_summary
from apps.sales.selectors import barber_display_name, item_display_name, local_today
from apps.sales.services.checkout import MAX_PARTS
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import role_has_permission

OTHER_DAY_CLOSED = "Cerradas"


def order_row(order: Order) -> dict:
    row = board_row(order)
    return {
        "id": order.public_id,
        "number": order.number,
        "status": order.status,
        "client_name": row["client"],
        "barbers": row["barbers"],
        "items": row["items"],
        "payment": row["payment"],
        "total": order.total,
        "created_at": order.created_at,
        "closed_at": order.closed_at,
        "cancel_reason": order.cancel_reason,
    }


def _tab_labels(day: date, today: date) -> dict[str, str]:
    """ "Cerradas hoy" solo si el día es hoy."""
    labels = dict(TABS)
    if day != today:
        labels[CLOSED_TODAY] = OTHER_DAY_CLOSED
    return labels


def order_list(membership: Membership, *, scope: BranchScope, filters: BoardFilter, page: int) -> dict:
    """Una página de la pestaña, el conteo de cada pestaña y, en las cerradas, lo cobrado del día."""
    orders = board_orders(membership, scope=scope, filters=filters, page=page)
    counts = tab_counts(membership, scope=scope, day=filters.day)
    summary = closed_today_summary(membership, scope=scope, day=filters.day) if filters.tab == CLOSED_TODAY else None
    today = local_today(membership)
    labels = _tab_labels(filters.day or today, today)
    return {
        "tab": filters.tab,
        "day": filters.day or today,
        "tabs": [{"value": value, "label": labels[value], "count": counts[value]} for value, _ in TABS],
        "summary": summary,
        "count": orders.paginator.count,
        "page": orders.number,
        "pages": orders.paginator.num_pages,
        "page_size": orders.paginator.per_page,
        "results": [order_row(order) for order in orders],
        "stale_cash": stale_session(membership, scope=scope) is not None,
    }


def _client(order: Order, profile: dict | None) -> dict | None:
    if order.client is None:
        return None
    return {
        "id": order.client.public_id,
        "name": order.client.full_name,
        "phone": mask_phone(order.client.phone) or None,
        "level": profile["status"].label if profile else None,
        "visits": profile["visits"] if profile else 0,
    }


def _lines(order: Order) -> list[dict]:
    return [
        {
            "id": line.public_id,
            "kind": line.item_type,
            "kind_label": line.get_item_type_display(),
            "name": item_display_name(line),
            "barber": barber_display_name(line.barber),
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "line_total": line.line_total,
        }
        for line in order.items.all()
    ]


def _payments(order: Order) -> list[dict]:
    return [
        {"method": payment.get_method_display(), "amount": payment.amount, "reference": payment.reference}
        for payment in order.payments.all()
    ]


def _actions(membership: Membership, order: Order, *, writable: bool) -> dict[str, bool]:
    """Lo que el rol puede hacer con la comanda en su estado; anular una cerrada exige comandas.anular.

    En "todas" no se escribe (`branch_for_write`): ninguna acción.
    """
    can = {code: role_has_permission(membership.role, f"comandas.{code}") for code in ("editar", "descontar", "cerrar")}
    editable = writable and order.status in EDITABLE_STATUSES
    closed = writable and order.status == OrderStatus.CLOSED
    return {
        "edit": editable and can["editar"],
        "discount": editable and can["descontar"],
        "checkout": editable and can["cerrar"],
        "cancel": (editable and can["editar"]) or (closed and role_has_permission(membership.role, "comandas.anular")),
    }


def order_detail(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> dict:
    summary = order_summary(membership, public_id, scope=scope)
    order = summary["order"]
    return {
        **order_row(order),
        "branch": order.branch.name,
        "editable": summary["editable"],
        "client": _client(order, summary["client"]),
        "barber": barber_display_name(order.barber),
        "lines": _lines(order),
        "subtotal": order.subtotal,
        "discount": order.discount,
        "discount_reason": order.discount_reason,
        "amount_paid": order.amount_paid,
        "balance": order.balance,
        "payments": _payments(order),
        "credit": summary["credit"],
        "actions": _actions(membership, order, writable=scope.branch is not None),
    }


def order_catalog(membership: Membership, *, scope: BranchScope) -> dict:
    """Lo que piden los formularios: barberos activos, servicios y productos con su precio y stock en la sede
    y las formas de pago habilitadas. En "todas" no hay precio de sede: se pide elegir una."""
    limits = {"max_parts": MAX_PARTS, "max_quantity": MAX_LINE_QUANTITY}
    if scope.branch is None:
        empty = {"barbers": [], "services": [], "products": [], "methods": []}
        return {"needs_branch": True, "branch": None, **empty, **limits}
    catalog = catalog_for_branch(membership, scope=scope, branch=scope.branch)
    return {
        "needs_branch": False,
        "branch": scope.branch.name,
        "barbers": [{"id": barber.public_id, "name": barber.display_name} for barber in catalog["barbers"]],
        "services": [
            {"id": service.public_id, "name": service.name, "price": service.price_now}
            for service in catalog["services"]
        ],
        "products": [
            {"id": product.public_id, "name": product.name, "price": product.price_now, "stock": product.stock}
            for product in catalog["products"]
        ],
        "methods": [{"value": value, "label": label} for value, label in payment_methods()],
        **limits,
    }


def client_choice(client: Client) -> dict:
    """Solo lo de la barbería (nombre y celular enmascarado): ni historial ni fiados de ninguna sede."""
    return {"id": client.public_id, "name": client.full_name, "phone": mask_phone(client.phone) or None}
