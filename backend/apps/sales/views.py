"""Pantalla de Comandas (fase F3): la lista por pestañas, el detalle de una comanda y el cobro rápido.

Las vistas solo reciben, validan el formato y responden; leen con `apps.sales.board` y
`apps.sales.order_page`, y escriben en `apps.sales.actions` con los services. Todo por el alcance de
sede de la petición: la comanda de otra sede no se encuentra (404), igual que la de otra barbería.
"""

from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.cash.board import stale_session
from apps.cash.selectors import payment_methods
from apps.clients.selectors import list_clients
from apps.sales.board import CLOSED_TODAY, TABS, board_orders, board_row, closed_today_summary, tab_counts
from apps.sales.forms import BoardFilterForm
from apps.sales.models import Order
from apps.sales.order_page import catalog_for_branch, order_page
from apps.sales.selectors import local_today
from apps.staff.selectors import barbers_in_scope
from apps.tenancy.permissions import require_permission
from apps.tenancy.roles import role_has_permission

BOARD = "orders/board.html"
NEW_ORDER = "orders/new.html"
QUICK_CHARGE = "orders/quick.html"
CLIENT_RESULTS = 20
PERMISSIONS = {
    "create": "comandas.crear",
    "quick": "comandas.cerrar",
    "edit": "comandas.editar",
    "discount": "comandas.descontar",
    "close": "comandas.cerrar",
    "cancel_closed": "comandas.anular",
}


def _can(membership) -> dict[str, bool]:
    return {name: role_has_permission(membership.role, code) for name, code in PERMISSIONS.items()}


def _board(request: HttpRequest) -> dict:
    membership, scope = request.membership, request.branch_scope
    filters = BoardFilterForm(request.GET).filters()
    counts = tab_counts(membership, scope=scope)
    return {
        "filters": filters,
        "tabs": [{"value": value, "label": label, "count": counts[value]} for value, label in TABS],
        "rows": [board_row(order) for order in board_orders(membership, scope=scope, filters=filters)],
        "summary": closed_today_summary(membership, scope=scope) if filters.tab == CLOSED_TODAY else None,
        "barbers": barbers_in_scope(membership, scope).filter(deleted_at__isnull=True).order_by("display_name"),
        "today": local_today(membership),
        "can": _can(membership),
        "stale_cash": stale_session(membership, scope=scope),
    }


@require_GET
@require_permission("comandas.ver")
def board(request: HttpRequest) -> HttpResponse:
    return render(request, BOARD, _board(request))


@require_GET
@require_permission("comandas.ver")
def detail(request: HttpRequest, public_id: UUID) -> HttpResponse:
    try:
        selected = order_page(request.membership, public_id, scope=request.branch_scope)
    except Order.DoesNotExist as exc:
        raise Http404 from exc
    search = _client_search(request) if request.GET.get("buscar_cliente") is not None else None
    context = {**_board(request), "selected": selected, "client_search": search, "methods": payment_methods()}
    return render(request, BOARD, context)


def _client_search(request: HttpRequest) -> dict:
    """Buscador de "Cambiar cliente": clientes de la barbería por nombre, celular o documento, por GET."""
    term = request.GET.get("buscar_cliente", "")[:60].strip()
    results = list(list_clients(request.membership, term)[:CLIENT_RESULTS]) if term else []
    return {"term": term, "results": results}


@require_GET
@require_permission("comandas.crear")
def new_order(request: HttpRequest) -> HttpResponse:
    """Elegir el cliente (opcional) antes de abrir la comanda. Sin cliente no podrá quedar como fiado."""
    term = request.GET.get("cliente", "")[:60]
    clients = list_clients(request.membership, term)[:CLIENT_RESULTS] if term else []
    return render(request, NEW_ORDER, {"term": term, "clients": clients})


@require_GET
@require_permission("comandas.cerrar")
def quick_charge(request: HttpRequest) -> HttpResponse:
    """Un servicio o un producto cobrado completo. En "todas" no se cobra: se pide elegir una sede."""
    scope = request.branch_scope
    if scope.branch is None:
        return render(request, QUICK_CHARGE, {"needs_branch": True})
    catalog = catalog_for_branch(request.membership, scope=scope, branch=scope.branch)
    return render(request, QUICK_CHARGE, {**catalog, "methods": payment_methods()})
