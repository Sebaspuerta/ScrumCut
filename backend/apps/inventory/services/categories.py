"""Categorías de productos (regla 37)."""

from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Product, ProductCategory
from apps.inventory.services._shared import _audit, _save_validated, _soft_delete_locked_product
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _category_snapshot(category: ProductCategory) -> dict:
    return {"name": category.name, "deleted_at": category.deleted_at.isoformat() if category.deleted_at else None}


def _live_category_for_update(public_id: UUID | str) -> ProductCategory:
    return ProductCategory.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


def create_category(membership: Membership, *, name: str) -> ProductCategory:
    ensure_permission(membership, "inventario.crear")
    with transaction.atomic():
        category = ProductCategory(barbershop_id=membership.barbershop_id, name=(name or "").strip())
        _save_validated(category, "Ya existe una categoría con ese nombre.")
        _audit(membership, "categoria_producto.crear", obj=category, before=None, after=_category_snapshot(category))
    return category


def update_category(membership: Membership, public_id: UUID | str, *, name: str) -> ProductCategory:
    ensure_permission(membership, "inventario.editar")
    with transaction.atomic():
        category = _live_category_for_update(public_id)
        before = _category_snapshot(category)
        category.name = (name or "").strip()
        _save_validated(category, "Ya existe una categoría con ese nombre.")
        after = _category_snapshot(category)
        if after != before:
            _audit(membership, "categoria_producto.editar", obj=category, before=before, after=after)
    return category


def soft_delete_category(membership: Membership, public_id: UUID | str, *, delete_products: bool) -> ProductCategory:
    """Regla 37. `delete_products` es obligatorio para que la elección sea explícita:

    - False: sus productos vivos quedan sin categoría.
    - True: sus productos vivos se borran lógicamente, cada uno con su auditoría.
    """
    ensure_permission(membership, "inventario.eliminar")
    with transaction.atomic():
        category = _live_category_for_update(public_id)
        before = _category_snapshot(category)
        products = list(Product.objects.select_for_update().filter(category=category, deleted_at__isnull=True))
        affected = [str(product.public_id) for product in products]
        if delete_products:
            for product in products:
                _soft_delete_locked_product(membership, product)
        else:
            Product.objects.filter(pk__in=[p.pk for p in products]).update(category=None, updated_at=timezone.now())
        category.soft_delete(by=membership.user)
        key = "deleted_products" if delete_products else "uncategorized_products"
        after = {**_category_snapshot(category), key: affected}
        _audit(membership, "categoria_producto.eliminar", obj=category, before=before, after=after)
    return category
