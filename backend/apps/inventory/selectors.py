"""Lecturas de inventario. Los managers ya filtran por la barbería activa.

Fase S4b de docs/sedes.md: el catálogo de productos es común a la barbería, pero las existencias
son de cada sede. Las lecturas de stock van por el alcance: la sede activa o, en "todas", cada
sede con el total de la barbería.
"""

from datetime import timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db.models import F, IntegerField, OuterRef, Q, QuerySet, Subquery, Sum, Value
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone

from apps.catalog.models import Service
from apps.inventory.models import Product, ProductCategory, ServiceConsumable, StockLevel, StockMovement
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _live_products() -> QuerySet[Product]:
    return Product.objects.filter(deleted_at__isnull=True).select_related("category")


def _stock(scope: BranchScope) -> Coalesce:
    """Existencias del producto en el alcance: la sede activa o, en "todas", la suma de las sedes."""
    in_scope = None if scope.is_all else Q(stock_levels__branch=scope.branch)
    return Coalesce(Sum("stock_levels__quantity", filter=in_scope), Value(0), output_field=IntegerField())


def list_products(
    membership: Membership,
    *,
    scope: BranchScope,
    active_only: bool = True,
    category: UUID | str | None = None,
    uncategorized: bool = False,
    product_type: str | None = None,
    search: str | None = None,
) -> QuerySet[Product]:
    """El catálogo común, cada producto con `stock` del alcance."""
    ensure_permission(membership, "inventario.ver")
    scope.check(membership)
    products = _live_products()
    if active_only:
        products = products.filter(is_active=True)
    if uncategorized:
        products = products.filter(category__isnull=True)
    elif category is not None:
        products = products.filter(category__public_id=category)
    if product_type:
        products = products.filter(product_type=product_type)
    term = (search or "").strip()
    if term:
        products = products.filter(Q(name__icontains=term) | Q(supplier__icontains=term))
    return products.annotate(stock=_stock(scope)).order_by(Lower("name"))


def get_product(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> Product:
    """Incluye desactivados; nunca borrados. Con `stock` del alcance. Lanza `Product.DoesNotExist`."""
    ensure_permission(membership, "inventario.ver")
    scope.check(membership)
    return _live_products().annotate(stock=_stock(scope)).get(public_id=public_id)


def _levels(membership: Membership, scope: BranchScope) -> QuerySet[StockLevel]:
    """Existencias por producto y sede del alcance, con el total del producto en la barbería."""
    total = (
        StockLevel.objects.filter(product=OuterRef("product"))
        .values("product")
        .annotate(total=Sum("quantity"))
        .values("total")
    )
    levels = StockLevel.objects.filter(product__deleted_at__isnull=True).select_related("product", "branch")
    return scope.readable(membership, levels).annotate(product_total=Subquery(total))


def stock_levels(membership: Membership, *, scope: BranchScope) -> QuerySet[StockLevel]:
    """Las existencias de la sede activa; en "todas", cada producto por sede con su total."""
    ensure_permission(membership, "inventario.ver")
    return _levels(membership, scope).order_by(Lower("product__name"), "branch__name")


def low_stock(membership: Membership, *, scope: BranchScope) -> QuerySet[StockLevel]:
    """Existencias de productos activos en o por debajo de su mínimo, por sede (incluye agotados con mínimo)."""
    ensure_permission(membership, "inventario.ver")
    return (
        _levels(membership, scope)
        .filter(
            product__is_active=True, product__minimum_stock__isnull=False, quantity__lte=F("product__minimum_stock")
        )
        .order_by("quantity", Lower("product__name"))
    )


def expiring(membership: Membership, *, scope: BranchScope, days: int = 30) -> QuerySet[StockLevel]:
    """Existencias (> 0) de productos activos que vencen dentro de `days` días o ya vencieron, por sede."""
    ensure_permission(membership, "inventario.ver")
    today = timezone.now().astimezone(ZoneInfo(membership.barbershop.timezone)).date()
    return (
        _levels(membership, scope)
        .filter(
            quantity__gt=0,
            product__is_active=True,
            product__expiration_date__isnull=False,
            product__expiration_date__lte=today + timedelta(days=days),
        )
        .order_by("product__expiration_date", Lower("product__name"))
    )


def list_categories(membership: Membership) -> QuerySet[ProductCategory]:
    ensure_permission(membership, "inventario.ver")
    return ProductCategory.objects.filter(deleted_at__isnull=True).order_by(Lower("name"))


def list_movements(membership: Membership, product: UUID | str, *, scope: BranchScope) -> QuerySet[StockMovement]:
    """Movimientos del producto en las sedes del alcance."""
    ensure_permission(membership, "inventario.ver")
    movements = StockMovement.objects.filter(product__public_id=product).select_related("branch")
    return scope.readable(membership, movements).order_by("created_at", "pk")


def consumables_for(service: Service) -> QuerySet[ServiceConsumable]:
    """Insumos de un servicio. sales la llama al cerrar la comanda; no exige permiso."""
    return ServiceConsumable.objects.filter(service=service).select_related("product").order_by("pk")
