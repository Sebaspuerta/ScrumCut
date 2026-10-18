"""Productos: crear, editar, activar, borrar y su foto (reglas 30–32, 35 y 36)."""

import io
from datetime import date
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from apps.catalog import branch_prices
from apps.inventory.models import MovementType, Product, ProductBranchPrice, ProductCategory
from apps.inventory.services._shared import (
    _audit,
    _product_snapshot,
    _save_validated,
    _soft_delete_locked_product,
)
from apps.inventory.services.movements import apply_stock_movement
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

PHOTO_MAX_BYTES = 5 * 1024 * 1024
PHOTO_MAX_PIXELS = 40_000_000  # tope de descompresión antes de cargar la imagen
PHOTO_FORMATS = {"PNG", "JPEG", "WEBP"}
PHOTO_SIZE = 200


class ProductData(TypedDict, total=False):
    """Campos editables de un producto. `current_stock` no está: solo lo cambia un movimiento."""

    name: str
    category: UUID | str | None
    product_type: str
    purchase_cost: Decimal
    sale_price: Decimal
    minimum_stock: int | None
    expiration_date: date | None
    supplier: str


def _live_product_for_update(public_id: UUID | str) -> Product:
    return Product.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


def _resolve_category(public_id: UUID | str | None) -> ProductCategory | None:
    """Regla 31: categoría viva de esta barbería (la validación de FK de Django no filtra)."""
    if public_id is None:
        return None
    try:
        return ProductCategory.objects.get(public_id=public_id, deleted_at__isnull=True)
    except ProductCategory.DoesNotExist as exc:
        raise ValidationError({"category": "La categoría no existe."}) from exc


def _apply(product: Product, data: ProductData) -> None:
    unknown = set(data) - set(ProductData.__annotations__)
    if unknown:
        raise TypeError(f"Campos no editables o desconocidos: {sorted(unknown)}")
    for field in ("name", "supplier"):
        if field in data:
            setattr(product, field, (data[field] or "").strip())
    for field in ("product_type", "purchase_cost", "sale_price", "minimum_stock", "expiration_date"):
        if field in data:
            setattr(product, field, data[field])
    if "category" in data:
        product.category = _resolve_category(data["category"])


def create_product(membership: Membership, data: ProductData, *, initial_stock: int = 0) -> Product:
    """El stock inicial, si lo hay, entra como un movimiento "Inventario inicial"."""
    ensure_permission(membership, "inventario.crear")
    if initial_stock < 0:
        raise ValidationError({"initial_stock": "El stock inicial no puede ser negativo."})
    with transaction.atomic():
        product = Product(barbershop_id=membership.barbershop_id)
        _apply(product, data)
        _save_validated(product, "Ya existe un producto con ese nombre.")
        _audit(membership, "producto.crear", obj=product, before=None, after=_product_snapshot(product))
        if initial_stock:
            apply_stock_movement(
                product,
                initial_stock,
                movement_type=MovementType.ENTRY,
                reason="Inventario inicial",
                actor=membership,
            )
    return product


def update_product(membership: Membership, public_id: UUID | str, *, data: ProductData) -> Product:
    """Defecto 15: `current_stock` no se acepta aquí (TypeError); usa entradas o ajustes."""
    ensure_permission(membership, "inventario.editar")
    with transaction.atomic():
        product = _live_product_for_update(public_id)
        before = _product_snapshot(product)
        _apply(product, data)
        _save_validated(product, "Ya existe un producto con ese nombre.")
        after = _product_snapshot(product)
        if after != before:
            _audit(membership, "producto.editar", obj=product, before=before, after=after)
    return product


def _set_product_active(membership: Membership, public_id: UUID | str, *, active: bool) -> Product:
    ensure_permission(membership, "inventario.editar")
    with transaction.atomic():
        product = _live_product_for_update(public_id)
        if product.is_active == active:
            return product
        before = _product_snapshot(product)
        product.is_active = active
        product.save(update_fields=["is_active", "updated_at"])
        action = "producto.activar" if active else "producto.desactivar"
        _audit(membership, action, obj=product, before=before, after=_product_snapshot(product))
    return product


def deactivate_product(membership: Membership, public_id: UUID | str) -> Product:
    return _set_product_active(membership, public_id, active=False)


def activate_product(membership: Membership, public_id: UUID | str) -> Product:
    return _set_product_active(membership, public_id, active=True)


def soft_delete_product(membership: Membership, public_id: UUID | str) -> Product:
    """Regla 35: borrado lógico; ventas y movimientos ya registrados quedan intactos."""
    ensure_permission(membership, "inventario.eliminar")
    with transaction.atomic():
        product = _live_product_for_update(public_id)
        _soft_delete_locked_product(membership, product)
    return product


def upload_product_photo(membership: Membership, public_id: UUID | str, *, upload) -> Product:
    """Regla 36: el formato se decide con Pillow sobre el contenido, nunca por la extensión.

    `upload` es un archivo (por ejemplo `UploadedFile`). Se guarda recortado al
    centro como PNG de 200 × 200; al recodificar se descartan los metadatos.
    """
    ensure_permission(membership, "inventario.editar")
    raw = upload.read(PHOTO_MAX_BYTES + 1)
    if not raw:
        raise ValidationError({"photo": "El archivo está vacío."})
    if len(raw) > PHOTO_MAX_BYTES:
        raise ValidationError({"photo": "La foto no puede pesar más de 5 MB."})
    try:
        image = Image.open(io.BytesIO(raw))
        if image.format not in PHOTO_FORMATS:
            raise ValidationError({"photo": "Formato no soportado. Usa PNG, JPEG o WEBP."})
        width, height = image.size
        if width * height > PHOTO_MAX_PIXELS:
            raise ValidationError({"photo": "La imagen es demasiado grande."})
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError({"photo": "El archivo no es una imagen válida."}) from exc

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    side = min(width, height)
    left, top = (width - side) // 2, (height - side) // 2
    thumbnail = image.crop((left, top, left + side, top + side)).resize(
        (PHOTO_SIZE, PHOTO_SIZE), Image.Resampling.LANCZOS
    )
    buffer = io.BytesIO()
    thumbnail.save(buffer, format="PNG")

    with transaction.atomic():
        product = _live_product_for_update(public_id)
        before = _product_snapshot(product)
        if product.photo:
            product.photo.delete(save=False)
        product.photo.save("foto.png", ContentFile(buffer.getvalue()), save=False)
        product.save(update_fields=["photo", "updated_at"])
        _audit(membership, "producto.foto", obj=product, before=before, after=_product_snapshot(product))
    return product


# ── Precio por sede (decisión 17 de docs/sedes.md) ───────────────────────────


def set_product_branch_price(
    membership: Membership, product: UUID | str, *, scope: BranchScope, price: Decimal
) -> ProductBranchPrice:
    """Precio de venta propio del producto en la sede del alcance; solo Dueño y Administrador."""
    target = Product.objects.get(public_id=product, deleted_at__isnull=True)
    return branch_prices.set_branch_price(membership, target, scope=scope, price=price)


def remove_product_branch_price(membership: Membership, product: UUID | str, *, scope: BranchScope) -> None:
    """La sede vuelve al precio de venta del catálogo."""
    target = Product.objects.get(public_id=product, deleted_at__isnull=True)
    branch_prices.remove_branch_price(membership, target, scope=scope)
