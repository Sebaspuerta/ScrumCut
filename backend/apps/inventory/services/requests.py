"""Entradas, ajustes y traslados con la llave del intento (la app de React).

Como el cobro rápido (`sales.services.quick_charge`): el diálogo manda la misma llave en cada reintento, así que
un doble envío o un reintento de red devuelve el movimiento ya registrado en vez de mover el stock otra vez. Entre
dos envíos simultáneos decide la restricción única de la base (`uq_stockmovement_request_key_per_barbershop`).
"""

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction

from apps.inventory.models import MovementType, StockMovement
from apps.inventory.services.movements import register_adjustment, register_entry, transfer_stock
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission


class StockRequestConflictError(Exception):
    """La llave ya registró otro movimiento: otro producto, cantidad, motivo, sede o persona. No se mueve nada."""


def _registered_with(request_key: UUID) -> StockMovement | None:
    return StockMovement.objects.filter(request_key=request_key).select_related("product", "branch").first()


def _once(request_key: UUID, register: Callable[[], StockMovement]) -> tuple[StockMovement, bool]:
    """El movimiento de la llave y si se registró ahora (False: ya estaba registrado con ella)."""
    try:
        with transaction.atomic():
            previous = _registered_with(request_key)
            if previous is None:
                return register(), True
    except IntegrityError:
        # Otro envío con la misma llave se registró mientras este esperaba: la base rechazó el segundo.
        previous = _registered_with(request_key)
        if previous is None:
            raise
    return previous, False


def _same_request(
    movement: StockMovement,
    membership: Membership,
    *,
    branch: Branch,
    product: UUID | str,
    movement_type: str,
    quantity: int,
    reason: str,
) -> bool:
    """La misma persona, en la misma sede, con el mismo producto, tipo, cantidad (con signo) y motivo."""
    return (
        movement.created_by_id == membership.user_id
        and movement.branch_id == branch.pk
        and str(movement.product.public_id) == str(product)
        and movement.movement_type == movement_type
        and movement.quantity == quantity
        and movement.reason == (reason or "").strip()
    )


def _start(membership: Membership, scope: BranchScope) -> Branch:
    """Permiso y sede antes de buscar la llave: en «todas» no se registra, tampoco un reenvío."""
    ensure_permission(membership, "inventario.ajustar")
    return scope.branch_for_write(membership)


def register_entry_once(
    membership: Membership,
    product: UUID | str,
    *,
    scope: BranchScope,
    request_key: UUID,
    quantity: int,
    reason: str,
    unit_cost: Decimal | None = None,
) -> tuple[StockMovement, bool]:
    """`register_entry` una sola vez por llave. Una llave ya usada con otros datos lanza `StockRequestConflictError`."""
    branch = _start(membership, scope)
    movement, registered = _once(
        request_key,
        lambda: register_entry(
            membership,
            product,
            scope=scope,
            quantity=quantity,
            reason=reason,
            unit_cost=unit_cost,
            request_key=request_key,
        ),
    )
    expected = {"product": product, "movement_type": MovementType.ENTRY, "quantity": quantity, "reason": reason}
    same_cost = unit_cost is None or movement.unit_cost == unit_cost
    if not (same_cost and _same_request(movement, membership, branch=branch, **expected)):
        raise StockRequestConflictError
    return movement, registered


def register_adjustment_once(
    membership: Membership,
    product: UUID | str,
    *,
    scope: BranchScope,
    request_key: UUID,
    quantity: int,
    reason: str,
) -> tuple[StockMovement, bool]:
    """`register_adjustment` una sola vez por llave, con la misma regla de conflicto que la entrada."""
    branch = _start(membership, scope)
    movement, registered = _once(
        request_key,
        lambda: register_adjustment(
            membership, product, scope=scope, quantity=quantity, reason=reason, request_key=request_key
        ),
    )
    expected = {"product": product, "movement_type": MovementType.ADJUSTMENT, "quantity": quantity, "reason": reason}
    if not _same_request(movement, membership, branch=branch, **expected):
        raise StockRequestConflictError
    return movement, registered


def _arrival(departure: StockMovement) -> StockMovement:
    """La entrada en el destino del traslado: comparte el `transfer_id` de la salida, que lleva la llave."""
    return StockMovement.objects.select_related("branch").get(
        transfer_id=departure.transfer_id, movement_type=MovementType.TRANSFER_IN
    )


def transfer_stock_once(
    membership: Membership,
    product: UUID | str,
    *,
    scope: BranchScope,
    request_key: UUID,
    destination: UUID | str,
    quantity: int,
    reason: str,
) -> tuple[tuple[StockMovement, StockMovement], bool]:
    """`transfer_stock` una sola vez por llave: las dos patas y si se registró ahora. La misma llave hacia otra sede,
    con otra cantidad u otro motivo lanza `StockRequestConflictError`."""
    branch = _start(membership, scope)
    legs: dict[str, StockMovement] = {}

    def register() -> StockMovement:
        legs["out"], legs["into"] = transfer_stock(
            membership,
            product,
            scope=scope,
            destination=destination,
            quantity=quantity,
            reason=reason,
            request_key=request_key,
        )
        return legs["out"]

    departure, registered = _once(request_key, register)
    expected = {"product": product, "movement_type": MovementType.TRANSFER_OUT, "quantity": -quantity, "reason": reason}
    if not _same_request(departure, membership, branch=branch, **expected):
        raise StockRequestConflictError
    arrival = legs["into"] if registered else _arrival(departure)
    if str(arrival.branch.public_id) != str(destination):
        raise StockRequestConflictError
    return (departure, arrival), registered
