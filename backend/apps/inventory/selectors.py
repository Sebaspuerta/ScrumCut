"""Lecturas de inventario. Los managers ya filtran por la barbería activa.

Fase S4b de docs/sedes.md: el catálogo de productos es común a la barbería, pero las existencias
son de cada sede. Las lecturas de stock van por el alcance: la sede activa o, en "todas", cada
sede con el total de la barbería.
"""

from datetime import timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db.models import (
    BooleanField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone

from apps.catalog.models import Service
from apps.inventory.models import Product, ProductCategory, ServiceConsumable, StockLevel, StockMovement
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission

# Una existencia en o por debajo del mínimo del producto (incluye la agotada con mínimo): la misma regla para la
# lista de stock bajo y para el aviso de cada producto.
AT_OR_BELOW_MINIMUM = Q(product__minimum_stock__isnull=False, quantity__lte=F("product__minimum_stock"))


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
    active: bool | None = True,
    category: UUID | str | None = None,
    uncategorized: bool = False,
    product_type: str | None = None,
    search: str | None = None,
) -> QuerySet[Product]:
    """El catálogo común, cada producto con `stock` del alcance. `active`: True activos, False inactivos, None todos."""
    ensure_permission(membership, "inventario.ver")
    scope.check(membership)
    products = _live_products()
    if active is not None:
        products = products.filter(is_active=active)
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
        .filter(AT_OR_BELOW_MINIMUM, product__is_active=True)
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


def with_scope_levels(membership: Membership, products: QuerySet[Product], *, scope: BranchScope) -> QuerySet[Product]:
    """Cada producto con `scope_levels`: sus existencias en las sedes del alcance, por nombre de sede, cada una con
    `is_low` (en o bajo el mínimo). Una sola consulta más para toda la lista."""
    low = ExpressionWrapper(AT_OR_BELOW_MINIMUM, output_field=BooleanField())
    levels = scope.readable(membership, StockLevel.objects.select_related("branch").annotate(is_low=low))
    return products.prefetch_related(Prefetch("stock_levels", levels.order_by("branch__name"), to_attr="scope_levels"))


def transfer_destinations(membership: Membership, product: Product, *, scope: BranchScope) -> QuerySet[Branch]:
    """Las sedes activas a las que se puede trasladar desde la sede del alcance, cada una con el `stock` del producto.

    Las mismas que acepta `services.transfer_stock`: activas, de la barbería y distintas del origen. En «todas»,
    ninguna (no hay origen).
    """
    ensure_permission(membership, "inventario.ajustar")
    scope.check(membership)
    if scope.branch is None:
        return Branch.objects.none()
    here = Q(stock_levels__product=product)
    stock = Coalesce(Sum("stock_levels__quantity", filter=here), Value(0), output_field=IntegerField())
    return Branch.objects.filter(is_active=True).exclude(pk=scope.branch.pk).annotate(stock=stock).order_by("name")


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
