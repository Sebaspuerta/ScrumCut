"""Escrituras de inventario.

Reglas portadas de MAGNUS v1 (`inventory_service.py`, `category_service.py`,
`service_consumable_service.py`), numeradas como en `docs/migracion-magnus.md`:
30–37 y 40. Defectos corregidos: 14 (bloqueo al tocar stock), 15 (el stock solo
cambia con un movimiento) y 16 (los movimientos son solo-agregar).

Igual que en las demás apps: un objeto inexistente, de otra barbería o borrado
lanza `DoesNotExist`; los datos inválidos, `ValidationError`.
"""

import io
from datetime import date
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from apps.audit.models import record
from apps.catalog.models import Service
from apps.inventory.models import MovementType, Product, ProductCategory, ServiceConsumable, StockMovement
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

_CENTS = Decimal("0.01")

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


def _audit(actor: Membership, action: str, obj, *, before: dict | None, after: dict | None) -> None:
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


def _category_snapshot(category: ProductCategory) -> dict:
    return {"name": category.name, "deleted_at": category.deleted_at.isoformat() if category.deleted_at else None}


def _consumable_snapshot(consumable: ServiceConsumable) -> dict:
    return {
        "service": str(consumable.service.public_id),
        "product": str(consumable.product.public_id),
        "quantity": consumable.quantity,
    }


def _save_validated(obj, duplicate_message: str) -> None:
    obj.full_clean()
    try:
        with transaction.atomic():
            obj.save()
    except IntegrityError as exc:
        # Dos solicitudes simultáneas pueden pasar full_clean con el mismo nombre: decide la base.
        raise ValidationError(duplicate_message) from exc


def _live_product_for_update(public_id: UUID | str) -> Product:
    return Product.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


def _live_category_for_update(public_id: UUID | str) -> ProductCategory:
    return ProductCategory.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


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


def _clean_reason(reason: str) -> str:
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ValidationError({"reason": "El motivo es obligatorio."})
    return cleaned


# ── Stock: la única puerta ───────────────────────────────────────────────────


def apply_stock_movement(
    product: Product,
    delta: int,
    movement_type: str,
    reason: str,
    actor: Membership,
    unit_cost: Decimal | None = None,
) -> StockMovement:
    """Única forma de cambiar `current_stock`. La usan entradas, ajustes y sales.

    Bloquea el producto, valida que el stock no quede negativo, lo actualiza con
    `F()` y deja el movimiento con el stock antes y después y el costo unitario.
    No valida permisos: lo hace la operación que la llama.
    """
    if delta == 0:
        raise ValidationError({"quantity": "La cantidad no puede ser cero."})
    reason = _clean_reason(reason)
    with transaction.atomic():
        locked = Product.objects.select_for_update().get(pk=product.pk)
        stock_before = locked.current_stock
        stock_after = stock_before + delta
        if stock_after < 0:
            raise ValidationError(
                f"Stock insuficiente de {locked.name}: hay {stock_before} y se necesitan {-delta}.",
                code="insufficient_stock",
            )
        Product.objects.filter(pk=locked.pk).update(current_stock=F("current_stock") + delta, updated_at=timezone.now())
        movement = StockMovement(
            barbershop_id=locked.barbershop_id,
            product=locked,
            movement_type=movement_type,
            quantity=delta,
            stock_before=stock_before,
            stock_after=stock_after,
            unit_cost=locked.purchase_cost if unit_cost is None else unit_cost,
            reason=reason,
            created_by=actor.user,
        )
        movement.full_clean()
        movement.save()
    product.current_stock = stock_after
    return movement


def register_entry(
    membership: Membership, product: UUID | str, quantity: int, reason: str, unit_cost: Decimal | None = None
) -> StockMovement:
    """Regla 33: entrada con cantidad > 0 y motivo."""
    ensure_permission(membership, "inventario.ajustar")
    if quantity <= 0:
        raise ValidationError({"quantity": "La cantidad de una entrada debe ser mayor que cero."})
    with transaction.atomic():
        target = Product.objects.get(public_id=product, deleted_at__isnull=True)
        return apply_stock_movement(target, quantity, MovementType.ENTRY, reason, membership, unit_cost)


def register_adjustment(membership: Membership, product: UUID | str, quantity: int, reason: str) -> StockMovement:
    """Regla 34: ajuste con signo y motivo; nunca deja el stock negativo."""
    ensure_permission(membership, "inventario.ajustar")
    with transaction.atomic():
        target = Product.objects.get(public_id=product, deleted_at__isnull=True)
        return apply_stock_movement(target, quantity, MovementType.ADJUSTMENT, reason, membership)


# ── Productos ────────────────────────────────────────────────────────────────


def create_product(membership: Membership, data: ProductData, initial_stock: int = 0) -> Product:
    """El stock inicial, si lo hay, entra como un movimiento "Inventario inicial"."""
    ensure_permission(membership, "inventario.crear")
    if initial_stock < 0:
        raise ValidationError({"initial_stock": "El stock inicial no puede ser negativo."})
    with transaction.atomic():
        product = Product(barbershop_id=membership.barbershop_id)
        _apply(product, data)
        _save_validated(product, "Ya existe un producto con ese nombre.")
        _audit(membership, "producto.crear", product, before=None, after=_product_snapshot(product))
        if initial_stock:
            apply_stock_movement(product, initial_stock, MovementType.ENTRY, "Inventario inicial", membership)
    return product


def update_product(membership: Membership, public_id: UUID | str, data: ProductData) -> Product:
    """Defecto 15: `current_stock` no se acepta aquí (TypeError); usa entradas o ajustes."""
    ensure_permission(membership, "inventario.editar")
    with transaction.atomic():
        product = _live_product_for_update(public_id)
        before = _product_snapshot(product)
        _apply(product, data)
        _save_validated(product, "Ya existe un producto con ese nombre.")
        after = _product_snapshot(product)
        if after != before:
            _audit(membership, "producto.editar", product, before=before, after=after)
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
        _audit(membership, action, product, before=before, after=_product_snapshot(product))
    return product


def deactivate_product(membership: Membership, public_id: UUID | str) -> Product:
    return _set_product_active(membership, public_id, active=False)


def activate_product(membership: Membership, public_id: UUID | str) -> Product:
    return _set_product_active(membership, public_id, active=True)


def _soft_delete_locked_product(membership: Membership, product: Product) -> None:
    before = _product_snapshot(product)
    product.soft_delete(by=membership.user)
    _audit(membership, "producto.eliminar", product, before=before, after=_product_snapshot(product))


def soft_delete_product(membership: Membership, public_id: UUID | str) -> Product:
    """Regla 35: borrado lógico; ventas y movimientos ya registrados quedan intactos."""
    ensure_permission(membership, "inventario.eliminar")
    with transaction.atomic():
        product = _live_product_for_update(public_id)
        _soft_delete_locked_product(membership, product)
    return product


def upload_product_photo(membership: Membership, public_id: UUID | str, upload) -> Product:
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
        _audit(membership, "producto.foto", product, before=before, after=_product_snapshot(product))
    return product


# ── Categorías ───────────────────────────────────────────────────────────────


def create_category(membership: Membership, *, name: str) -> ProductCategory:
    ensure_permission(membership, "inventario.crear")
    with transaction.atomic():
        category = ProductCategory(barbershop_id=membership.barbershop_id, name=(name or "").strip())
        _save_validated(category, "Ya existe una categoría con ese nombre.")
        _audit(membership, "categoria_producto.crear", category, before=None, after=_category_snapshot(category))
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
            _audit(membership, "categoria_producto.editar", category, before=before, after=after)
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
        _audit(membership, "categoria_producto.eliminar", category, before=before, after=after)
    return category


# ── Insumos de servicios (regla 40) ──────────────────────────────────────────


def add_consumable(
    membership: Membership, service: UUID | str, product: UUID | str, quantity: int
) -> ServiceConsumable:
    """Servicio y producto activos y vivos; un solo registro por par; cantidad > 0."""
    ensure_permission(membership, "servicios.editar")
    try:
        target_service = Service.objects.get(public_id=service, deleted_at__isnull=True, is_active=True)
    except Service.DoesNotExist as exc:
        raise ValidationError({"service": "El servicio no existe o está inactivo."}) from exc
    try:
        target_product = Product.objects.get(public_id=product, deleted_at__isnull=True, is_active=True)
    except Product.DoesNotExist as exc:
        raise ValidationError({"product": "El producto no existe o está inactivo."}) from exc
    with transaction.atomic():
        consumable = ServiceConsumable(
            barbershop_id=membership.barbershop_id, service=target_service, product=target_product, quantity=quantity
        )
        _save_validated(consumable, "Ese producto ya es insumo del servicio.")
        _audit(membership, "insumo.crear", consumable, before=None, after=_consumable_snapshot(consumable))
    return consumable


def update_consumable(membership: Membership, public_id: UUID | str, quantity: int) -> ServiceConsumable:
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        consumable = ServiceConsumable.objects.select_for_update().get(public_id=public_id)
        before = _consumable_snapshot(consumable)
        consumable.quantity = quantity
        consumable.full_clean()
        consumable.save(update_fields=["quantity", "updated_at"])
        _audit(membership, "insumo.editar", consumable, before=before, after=_consumable_snapshot(consumable))
    return consumable


def remove_consumable(membership: Membership, public_id: UUID | str) -> None:
    """Borrado físico: es configuración, no historial. La auditoría guarda lo que había."""
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        consumable = ServiceConsumable.objects.select_for_update().get(public_id=public_id)
        _audit(membership, "insumo.eliminar", consumable, before=_consumable_snapshot(consumable), after=None)
        consumable.delete()
