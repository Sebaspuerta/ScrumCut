"""Lecturas de inventario. Los managers ya filtran por la barbería activa."""

from datetime import timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db.models import F, Q, QuerySet
from django.db.models.functions import Lower
from django.utils import timezone

from apps.catalog.models import Service
from apps.inventory.models import Product, ProductCategory, ServiceConsumable, StockMovement
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _live_products() -> QuerySet[Product]:
    return Product.objects.filter(deleted_at__isnull=True).select_related("category")


def list_products(
    membership: Membership,
    *,
    active_only: bool = True,
    category: UUID | str | None = None,
    uncategorized: bool = False,
    product_type: str | None = None,
    search: str | None = None,
) -> QuerySet[Product]:
    ensure_permission(membership, "inventario.ver")
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
    return products.order_by(Lower("name"))


def get_product(membership: Membership, public_id: UUID | str) -> Product:
    """Incluye desactivados; nunca borrados. Lanza `Product.DoesNotExist`."""
    ensure_permission(membership, "inventario.ver")
    return _live_products().get(public_id=public_id)


def low_stock(membership: Membership) -> QuerySet[Product]:
    """Productos activos con stock en o por debajo de su mínimo (incluye agotados con mínimo)."""
    ensure_permission(membership, "inventario.ver")
    return (
        _live_products()
        .filter(is_active=True, minimum_stock__isnull=False, current_stock__lte=F("minimum_stock"))
        .order_by("current_stock", Lower("name"))
    )


def expiring(membership: Membership, days: int = 30) -> QuerySet[Product]:
    """Activos que vencen dentro de `days` días (contados en la zona de la barbería), o ya vencidos."""
    ensure_permission(membership, "inventario.ver")
    today = timezone.now().astimezone(ZoneInfo(membership.barbershop.timezone)).date()
    return (
        _live_products()
        .filter(is_active=True, expiration_date__isnull=False, expiration_date__lte=today + timedelta(days=days))
        .order_by("expiration_date", Lower("name"))
    )


def list_categories(membership: Membership) -> QuerySet[ProductCategory]:
    ensure_permission(membership, "inventario.ver")
    return ProductCategory.objects.filter(deleted_at__isnull=True).order_by(Lower("name"))


def list_movements(membership: Membership, product: UUID | str) -> QuerySet[StockMovement]:
    ensure_permission(membership, "inventario.ver")
    return StockMovement.objects.filter(product__public_id=product).order_by("created_at", "pk")


def consumables_for(service: Service) -> QuerySet[ServiceConsumable]:
    """Insumos de un servicio. sales la llama al cerrar la comanda; no exige permiso."""
    return ServiceConsumable.objects.filter(service=service).select_related("product").order_by("pk")
