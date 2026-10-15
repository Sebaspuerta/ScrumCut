"""Anulación de comanda con reversos (defecto 12): fiado, pagos devueltos y stock restituido."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cash.models import Direction, MovementKind
from apps.cash.selectors import open_session_for
from apps.cash.services import record_money
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.services import apply_stock_movement
from apps.receivables import services as receivables
from apps.sales.models import EDITABLE_STATUSES, Order, OrderStatus
from apps.sales.services._shared import _audit, _locked_order, _order_snapshot, _stock_reference
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_member, ensure_permission


def cancel_order(membership: Membership, order: UUID | str, *, reason: str) -> Order:
    """Abierta o en espera: se anula sin efectos (`comandas.editar`).

    Cerrada (`comandas.anular`, defecto 12): se anula su fiado si no tiene abonos,
    se devuelve cada pago como salida de la caja abierta de la sede y se restituye
    exactamente el stock que se descontó al cerrar.
    """
    ensure_member(membership)
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "El motivo de anulación es obligatorio."})
    with transaction.atomic():
        locked = _locked_order(membership, order)
        before = _order_snapshot(locked)
        if locked.status in EDITABLE_STATUSES:
            ensure_permission(membership, "comandas.editar")
        elif locked.status == OrderStatus.CLOSED:
            ensure_permission(membership, "comandas.anular")
            _reverse_closed(membership, locked, reason=reason)
        else:
            raise ValidationError("La comanda ya está anulada.", code="already_cancelled")
        locked.status = OrderStatus.CANCELLED
        locked.cancelled_at = timezone.now()
        locked.cancelled_by = membership.user
        locked.cancel_reason = reason
        locked.full_clean()
        locked.save()
        _audit(
            membership,
            "comanda.anular",
            order=locked,
            before=before,
            after={**_order_snapshot(locked), "reason": reason},
        )
    return locked


def _reverse_closed(membership: Membership, order: Order, *, reason: str) -> None:
    receivables.cancel_for_order(order, membership, reason=reason)

    payments = list(order.payments.order_by("pk"))
    if payments:
        session = open_session_for(order.branch)
        if session is None:
            raise ValidationError(
                "No hay una caja abierta en esta sede para devolver los pagos.", code="no_open_session"
            )
        for payment in payments:
            record_money(
                session,
                MovementKind.REFUND,
                direction=Direction.OUT,
                method=payment.method,
                amount=payment.amount,
                description=f"Devolución comanda #{order.number}",
                actor=membership,
            )

    reference = _stock_reference(order)
    sold = StockMovement.objects.filter(
        reference=reference, movement_type__in=(MovementType.SALE, MovementType.SERVICE)
    ).select_related("product")
    for movement in sold.order_by("pk"):
        apply_stock_movement(
            movement.product,
            -movement.quantity,
            movement_type=MovementType.REVERSAL,
            reason=f"Anulación comanda #{order.number}",
            actor=membership,
            unit_cost=movement.unit_cost,
            reference=reference,
        )
