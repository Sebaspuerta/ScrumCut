"""Movimientos de stock: la única puerta para cambiarlo (reglas 33 y 34, defectos 14, 15 y 16).

Fase S4b de docs/sedes.md: el stock es por sede (`StockLevel`). Entradas, ajustes y traslados
salen de la sede del alcance; el consumo de una comanda, de la sede de la comanda.
"""

import uuid
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.audit.models import record
from apps.inventory.models import MovementType, Product, StockLevel, StockMovement
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission

SAME_BRANCH = "El traslado necesita una sede de destino distinta a la de origen."


def _clean_reason(reason: str) -> str:
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ValidationError({"reason": "El motivo es obligatorio."})
    return cleaned


def _level_id(product: Product, branch: Branch) -> int:
    """La existencia del producto en la sede; si no existía, se crea en 0 (sin bloquearla todavía)."""
    level, _ = StockLevel.objects.get_or_create(
        product=product, branch=branch, defaults={"barbershop_id": product.barbershop_id}
    )
    return level.pk


def _locked_level(product: Product, branch: Branch) -> StockLevel:
    return StockLevel.objects.select_for_update().select_related("product", "branch").get(pk=_level_id(product, branch))


def _record(level: StockLevel, delta: int, *, movement_type: str, unit_cost: Decimal, **details) -> StockMovement:
    movement = StockMovement(
        barbershop_id=level.barbershop_id,
        product=level.product,
        branch=level.branch,
        movement_type=movement_type,
        quantity=delta,
        stock_before=level.quantity,
        stock_after=level.quantity + delta,
        unit_cost=unit_cost,
        **details,
    )
    movement.full_clean()
    movement.save()
    return movement


def apply_stock_movement(
    product: Product,
    delta: int,
    *,
    branch: Branch,
    movement_type: str,
    reason: str,
    actor: Membership,
    unit_cost: Decimal | None = None,
    reference: str = "",
    transfer_id: UUID | None = None,
) -> StockMovement:
    """Única forma de cambiar una existencia: la del producto en `branch`.

    Bloquea la existencia, valida que no quede negativa, la actualiza con `F()` y deja el
    movimiento con lo que había antes y después. No valida permisos ni sede: lo hace la
    operación que la llama.
    """
    if delta == 0:
        raise ValidationError({"quantity": "La cantidad no puede ser cero."})
    reason = _clean_reason(reason)
    with transaction.atomic():
        level = _locked_level(product, branch)
        if level.quantity + delta < 0:
            raise ValidationError(
                f"Stock insuficiente de {product.name} en {branch.name}: hay {level.quantity} y se necesitan {-delta}.",
                code="insufficient_stock",
            )
        cost = product.purchase_cost if unit_cost is None else unit_cost
        movement = _record(
            level,
            delta,
            movement_type=movement_type,
            unit_cost=cost,
            reason=reason,
            reference=reference,
            transfer_id=transfer_id,
            created_by=actor.user,
        )
        StockLevel.objects.filter(pk=level.pk).update(quantity=F("quantity") + delta, updated_at=timezone.now())
    return movement


def _live_product(public_id: UUID | str) -> Product:
    return Product.objects.get(public_id=public_id, deleted_at__isnull=True)


def register_entry(
    membership: Membership,
    product: UUID | str,
    *,
    scope: BranchScope,
    quantity: int,
    reason: str,
    unit_cost: Decimal | None = None,
) -> StockMovement:
    """Regla 33: entrada con cantidad > 0 y motivo, en la sede del alcance."""
    ensure_permission(membership, "inventario.ajustar")
    if quantity <= 0:
        raise ValidationError({"quantity": "La cantidad de una entrada debe ser mayor que cero."})
    branch = scope.branch_for_write(membership)
    with transaction.atomic():
        return apply_stock_movement(
            _live_product(product),
            quantity,
            branch=branch,
            movement_type=MovementType.ENTRY,
            reason=reason,
            actor=membership,
            unit_cost=unit_cost,
        )


def register_adjustment(
    membership: Membership, product: UUID | str, *, scope: BranchScope, quantity: int, reason: str
) -> StockMovement:
    """Regla 34: ajuste con signo y motivo en la sede del alcance; nunca deja la existencia negativa."""
    ensure_permission(membership, "inventario.ajustar")
    branch = scope.branch_for_write(membership)
    with transaction.atomic():
        return apply_stock_movement(
            _live_product(product),
            quantity,
            branch=branch,
            movement_type=MovementType.ADJUSTMENT,
            reason=reason,
            actor=membership,
        )


# ── Traslados (decisión 6) ───────────────────────────────────────────────────


def _destination(public_id: UUID | str, origin: Branch) -> Branch:
    """Activa y de esta barbería (el manager ya filtra por ella), y distinta del origen."""
    try:
        destination = Branch.objects.get(public_id=public_id, is_active=True)
    except (Branch.DoesNotExist, ValidationError) as exc:
        raise ValidationError({"destination": "La sede de destino no existe o está inactiva."}) from exc
    if destination.pk == origin.pk:
        raise ValidationError({"destination": SAME_BRANCH})
    return destination


def _lock_both(product: Product, origin: Branch, *, destination: Branch) -> None:
    """Bloquea las dos existencias siempre en el mismo orden (por id): dos traslados cruzados no se
    esperan mutuamente."""
    ids = [_level_id(product, branch) for branch in (origin, destination)]
    list(StockLevel.objects.select_for_update().filter(pk__in=ids).order_by("pk"))


def transfer_stock(
    membership: Membership,
    product: UUID | str,
    *,
    scope: BranchScope,
    destination: UUID | str,
    quantity: int,
    reason: str,
) -> tuple[StockMovement, StockMovement]:
    """Lleva unidades de la sede del alcance a otra sede activa de la barbería, en una sola transacción.

    Deja una salida en el origen y una entrada en el destino con el mismo `transfer_id`.
    No deja el origen en negativo.
    """
    ensure_permission(membership, "inventario.ajustar")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError({"quantity": "La cantidad del traslado debe ser un entero mayor que cero."})
    origin = scope.branch_for_write(membership)
    target = _destination(destination, origin)
    transfer_id = uuid.uuid4()
    with transaction.atomic():
        item = _live_product(product)
        _lock_both(item, origin, destination=target)
        common = {"reason": reason, "actor": membership, "transfer_id": transfer_id}
        out = apply_stock_movement(item, -quantity, branch=origin, movement_type=MovementType.TRANSFER_OUT, **common)
        into = apply_stock_movement(item, quantity, branch=target, movement_type=MovementType.TRANSFER_IN, **common)
        _audit_transfer(membership, item, origin=origin, destination=target, quantity=quantity, transfer_id=transfer_id)
    return out, into


def _audit_transfer(
    membership: Membership, product: Product, *, origin: Branch, destination: Branch, quantity: int, transfer_id: UUID
) -> None:
    record(
        action="inventario.trasladar",
        entity=product._meta.label,
        entity_id=str(product.public_id),
        actor=membership.user,
        barbershop=membership.barbershop,
        branch=origin,
        before=None,
        after={
            "origin": str(origin.public_id),
            "destination": str(destination.public_id),
            "quantity": quantity,
            "transfer_id": str(transfer_id),
        },
    )
