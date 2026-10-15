"""Movimientos de stock: la única puerta para cambiarlo (reglas 33 y 34, defectos 14, 15 y 16)."""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.inventory.models import MovementType, Product, StockMovement
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _clean_reason(reason: str) -> str:
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ValidationError({"reason": "El motivo es obligatorio."})
    return cleaned


def apply_stock_movement(
    product: Product,
    delta: int,
    *,
    movement_type: str,
    reason: str,
    actor: Membership,
    unit_cost: Decimal | None = None,
    reference: str = "",
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
            reference=reference,
            created_by=actor.user,
        )
        movement.full_clean()
        movement.save()
    product.current_stock = stock_after
    return movement


def register_entry(
    membership: Membership, product: UUID | str, *, quantity: int, reason: str, unit_cost: Decimal | None = None
) -> StockMovement:
    """Regla 33: entrada con cantidad > 0 y motivo."""
    ensure_permission(membership, "inventario.ajustar")
    if quantity <= 0:
        raise ValidationError({"quantity": "La cantidad de una entrada debe ser mayor que cero."})
    with transaction.atomic():
        target = Product.objects.get(public_id=product, deleted_at__isnull=True)
        return apply_stock_movement(
            target, quantity, movement_type=MovementType.ENTRY, reason=reason, actor=membership, unit_cost=unit_cost
        )


def register_adjustment(membership: Membership, product: UUID | str, *, quantity: int, reason: str) -> StockMovement:
    """Regla 34: ajuste con signo y motivo; nunca deja el stock negativo."""
    ensure_permission(membership, "inventario.ajustar")
    with transaction.atomic():
        target = Product.objects.get(public_id=product, deleted_at__isnull=True)
        return apply_stock_movement(
            target, quantity, movement_type=MovementType.ADJUSTMENT, reason=reason, actor=membership
        )
