"""Apoyo común a los módulos de escrituras de inventario: auditoría, guardado validado y borrado de productos."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.audit.models import record
from apps.inventory.models import Product
from apps.tenancy.models import Membership

_CENTS = Decimal("0.01")


def _audit(actor: Membership, action: str, *, obj, before: dict | None, after: dict | None) -> None:
    record(
        action=action,
        entity=obj._meta.label,
        entity_id=str(obj.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        before=before,
        after=after,
    )


def _money(value) -> str:
    return str(Decimal(value).quantize(_CENTS))


def _product_snapshot(product: Product) -> dict:
    return {
        "name": product.name,
        "category": str(product.category.public_id) if product.category_id else None,
        "product_type": product.product_type,
        "purchase_cost": _money(product.purchase_cost),
        "sale_price": _money(product.sale_price),
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "expiration_date": product.expiration_date.isoformat() if product.expiration_date else None,
        "supplier": product.supplier,
        "photo": product.photo.name or None,
        "is_active": product.is_active,
        "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
    }


def _save_validated(obj, duplicate_message: str) -> None:
    obj.full_clean()
    try:
        with transaction.atomic():
            obj.save()
    except IntegrityError as exc:
        # Dos solicitudes simultáneas pueden pasar full_clean con el mismo nombre: decide la base.
        raise ValidationError(duplicate_message) from exc


def _soft_delete_locked_product(membership: Membership, product: Product) -> None:
    """Lo usan el borrado de un producto y el de una categoría con sus productos."""
    before = _product_snapshot(product)
    product.soft_delete(by=membership.user)
    _audit(membership, "producto.eliminar", obj=product, before=before, after=_product_snapshot(product))
