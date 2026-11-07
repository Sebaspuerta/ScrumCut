"""Inventario en la app de React: el catálogo de productos con las existencias y el precio de la sede, en JSON.

El catálogo es de la barbería; las existencias, el precio efectivo y los movimientos, de las sedes del alcance
(decisiones 6 y 17 de docs/sedes.md). El precio efectivo es el de la sede si lo fijó; si no, el del catálogo
(`catalog.branch_prices.with_current_price`, la única regla). En «todas» no hay un precio de sede: va el del catálogo.
Qué acciones permite el rol lo decide el backend.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.core.paginator import Paginator
from django.db.models import F, QuerySet
from django.urls import reverse

from apps.api.cash import person
from apps.catalog.branch_prices import with_current_price
from apps.inventory import selectors
from apps.inventory.models import Product, ProductBranchPrice, ProductType, StockLevel, StockMovement
from apps.sales.selectors import local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import role_has_permission

PRODUCTS_PAGE_SIZE = 50
MOVEMENTS_PAGE_SIZE = 20
ALERTS_SHOWN = 10  # los más urgentes de cada aviso; el conteo dice cuántos hay
UNCATEGORIZED = "sin"
# El filtro de estado de la lista: activos (por defecto), inactivos o todos.
STATUSES = (("activos", "Activos"), ("inactivos", "Inactivos"), ("todos", "Todos"))
_ACTIVE_BY_STATUS = {"activos": True, "inactivos": False, "todos": None}


@dataclass(frozen=True)
class ProductFilter:
    search: str = ""
    category: str = ""
    product_type: str = ""
    status: str = STATUSES[0][0]


def photo_url(product: Product) -> str | None:
    """La foto se sirve por la API (sesión e inventario.ver), nunca por MEDIA. `v` cambia con cada edición del
    producto, así que el navegador no muestra una foto vieja."""
    if not product.photo:
        return None
    path = reverse("api_product_photo", kwargs={"public_id": product.public_id})
    return f"{path}?v={int(product.updated_at.timestamp())}"


def _priced(products: QuerySet[Product], scope: BranchScope) -> QuerySet[Product]:
    """`price_now`: el precio efectivo de la sede del alcance o, en «todas», el del catálogo."""
    if scope.branch is None:
        return products.annotate(price_now=F("sale_price"))
    return with_current_price(products, scope.branch)


def _level(level: StockLevel) -> dict:
    return {"branch": level.branch.name, "quantity": level.quantity, "low": level.is_low}


def product_row(product: Product) -> dict:
    """Un producto de la lista, con su existencia en el alcance, cada sede y si alguna está en o bajo el mínimo."""
    levels = product.scope_levels
    return {
        "id": product.public_id,
        "name": product.name,
        "category": product.category.name if product.category_id else None,
        "product_type": product.product_type,
        "type_label": product.get_product_type_display(),
        "photo": photo_url(product),
        "stock": product.stock,
        "price": product.price_now,
        "minimum_stock": product.minimum_stock,
        "low_stock": any(level.is_low for level in levels),
        "is_active": product.is_active,
        "levels": [_level(level) for level in levels],
    }


def _category_filter(category: str) -> dict:
    if category == UNCATEGORIZED:
        return {"uncategorized": True}
    return {"category": category or None}


def _options(choices) -> list[dict]:
    return [{"value": value, "label": label} for value, label in choices]


def product_list(membership: Membership, *, scope: BranchScope, filters: ProductFilter, page: int) -> dict:
    """Una página del catálogo con la existencia y el precio de la sede, y las opciones de cada filtro."""
    products = selectors.list_products(
        membership,
        scope=scope,
        active=_ACTIVE_BY_STATUS[filters.status],
        product_type=filters.product_type or None,
        search=filters.search,
        **_category_filter(filters.category),
    )
    listed = selectors.with_scope_levels(membership, _priced(products, scope), scope=scope)
    rows = Paginator(listed, PRODUCTS_PAGE_SIZE).get_page(page)
    categories = selectors.list_categories(membership)
    return {
        "search": filters.search,
        "category": filters.category,
        "product_type": filters.product_type,
        "status": filters.status,
        "categories": [{"value": str(c.public_id), "label": c.name} for c in categories],
        "types": _options(ProductType.choices),
        "statuses": _options(STATUSES),
        "count": rows.paginator.count,
        "page": rows.number,
        "pages": rows.paginator.num_pages,
        "page_size": rows.paginator.per_page,
        "results": [product_row(product) for product in rows],
    }


def _movement(movement: StockMovement) -> dict:
    return {
        "id": movement.public_id,
        "at": movement.created_at,
        "kind": movement.movement_type,
        "kind_label": movement.get_movement_type_display(),
        "branch": movement.branch.name,
        "quantity": movement.quantity,
        "stock_before": movement.stock_before,
        "stock_after": movement.stock_after,
        "unit_cost": movement.unit_cost,
        "reason": movement.reason,
        "by": person(movement.created_by),
    }


def _movements(membership: Membership, product: Product, *, scope: BranchScope, page: int) -> dict:
    """El historial de las sedes del alcance, lo más reciente primero."""
    movements = selectors.list_movements(membership, product.public_id, scope=scope)
    newest_first = movements.select_related("created_by").order_by("-created_at", "-pk")
    rows = Paginator(newest_first, MOVEMENTS_PAGE_SIZE).get_page(page)
    return {
        "count": rows.paginator.count,
        "page": rows.number,
        "pages": rows.paginator.num_pages,
        "page_size": rows.paginator.per_page,
        "results": [_movement(movement) for movement in rows],
    }


def _actions(membership: Membership, scope: BranchScope) -> dict[str, bool]:
    """Escribir existencias y precios exige una sede; los datos del catálogo se editan desde cualquier alcance."""
    role, one_branch = membership.role, scope.branch is not None
    return {
        "edit": role_has_permission(role, "inventario.editar"),
        "delete": role_has_permission(role, "inventario.eliminar"),
        "adjust": one_branch and role_has_permission(role, "inventario.ajustar"),
        "branch_price": one_branch and role_has_permission(role, "inventario.editar"),
    }


def _own_price(product: Product, scope: BranchScope):
    if scope.branch is None:
        return None
    own = ProductBranchPrice.objects.filter(product=product, branch=scope.branch).values_list("price", flat=True)
    return own.first()


def _destinations(membership: Membership, product: Product, scope: BranchScope, can_adjust: bool) -> list[dict]:
    """A dónde se puede trasladar desde esta sede, con lo que ya hay allá: el diálogo lo muestra antes de confirmar."""
    if not can_adjust:
        return []
    branches = selectors.transfer_destinations(membership, product, scope=scope)
    return [{"id": branch.public_id, "name": branch.name, "stock": branch.stock} for branch in branches]


def _product_fields(product: Product) -> dict:
    category = product.category
    return {
        "category": {"id": category.public_id, "name": category.name} if category else None,
        "purchase_cost": product.purchase_cost,
        "sale_price": product.sale_price,
        "expiration_date": product.expiration_date,
        "supplier": product.supplier,
    }


def product_detail(membership: Membership, public_id: UUID | str, *, scope: BranchScope, page: int = 1) -> dict:
    """El producto con su precio en la sede, sus existencias por sede, sus movimientos y lo que el rol puede hacer."""
    products = selectors.list_products(membership, scope=scope, active=None).filter(public_id=public_id)
    product = selectors.with_scope_levels(membership, _priced(products, scope), scope=scope).get()
    actions = _actions(membership, scope)
    can_write_stock = role_has_permission(membership.role, "inventario.ajustar")
    return {
        **product_row(product),
        **_product_fields(product),
        "branch_price": _own_price(product, scope),
        "branch": scope.branch.name if scope.branch else None,
        "movements": _movements(membership, product, scope=scope, page=page),
        "destinations": _destinations(membership, product, scope, actions["adjust"]),
        "actions": actions,
        "needs_branch": scope.branch is None and can_write_stock,
    }


def _alert(level: StockLevel, today: date) -> dict:
    product = level.product
    expiration = product.expiration_date
    return {
        "product": product.public_id,
        "name": product.name,
        "branch": level.branch.name,
        "quantity": level.quantity,
        "minimum_stock": product.minimum_stock,
        "expiration_date": expiration,
        "expired": expiration is not None and expiration < today,
    }


def stock_alerts(membership: Membership, *, scope: BranchScope) -> dict:
    """Stock bajo y perecederos por vencer de las sedes del alcance (los mismos selectores de las alertas)."""
    low = selectors.low_stock(membership, scope=scope)
    expiring = selectors.expiring(membership, scope=scope)
    today = local_today(membership)
    return {
        "low_stock": [_alert(level, today) for level in low[:ALERTS_SHOWN]],
        "low_stock_count": low.count(),
        "expiring": [_alert(level, today) for level in expiring[:ALERTS_SHOWN]],
        "expiring_count": expiring.count(),
    }
