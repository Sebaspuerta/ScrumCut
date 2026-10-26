"""Lecturas del detalle de una comanda en la pantalla de Comandas (fase F3).

La comanda se lee por el alcance (`get_order`: la de otra sede o de otro barbero no se encuentra).
Los precios del catálogo que se muestran salen de `with_current_price`, la misma regla con la que
`add_item` fija el precio de la línea; el formulario nunca manda un precio.
"""

from decimal import Decimal
from uuid import UUID

from apps.catalog.branch_prices import with_current_price
from apps.catalog.selectors import list_services
from apps.clients.selectors import client_profile
from apps.inventory.models import ProductType
from apps.inventory.selectors import list_products
from apps.receivables.selectors import client_balance
from apps.sales.models import EDITABLE_STATUSES, Order
from apps.sales.selectors import get_order
from apps.staff.selectors import barbers_in_scope
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import BarbershopSettings, Branch, Membership


def _credit(order: Order) -> dict | None:
    """Lo que el cliente debe en la sede de la comanda y, si la barbería fija un límite, su cupo."""
    if order.client is None:
        return None
    debt = client_balance(order.client, branch=order.branch)
    limit = BarbershopSettings.objects.get().max_credit_per_client
    return {"debt": debt, "available": None if limit is None else max(limit - debt, Decimal("0.00"))}


def _client(membership: Membership, order: Order, scope: BranchScope) -> dict | None:
    """Su historial y su nivel en las sedes del alcance (decisión 15); el celular va enmascarado."""
    if order.client is None:
        return None
    return client_profile(membership, order.client.public_id, scope=scope)


def catalog_for_branch(membership: Membership, *, scope: BranchScope, branch: Branch) -> dict:
    """Servicios y productos de venta con su precio en la sede, y los barberos del alcance."""
    products = list_products(membership, scope=scope, product_type=ProductType.SALE)
    return {
        "services": list(with_current_price(list_services(), branch)),
        "products": list(with_current_price(products, branch)),
        "barbers": list(barbers_in_scope(membership, scope).filter(is_active=True, deleted_at__isnull=True)),
    }


def order_summary(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> dict:
    """La comanda con sus líneas, su cliente y su fiado posible (la API pide el catálogo aparte)."""
    order = get_order(membership, public_id, scope=scope)
    return {
        "order": order,
        "editable": order.status in EDITABLE_STATUSES,
        "client": _client(membership, order, scope),
        "credit": _credit(order),
    }


def order_page(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> dict:
    """La comanda con sus líneas, su cliente, su fiado posible y lo que se le puede agregar."""
    summary = order_summary(membership, public_id, scope=scope)
    return {**summary, **catalog_for_branch(membership, scope=scope, branch=summary["order"].branch)}
