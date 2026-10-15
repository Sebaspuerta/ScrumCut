"""Apoyo común a los módulos de escrituras de comandas: auditoría, bloqueo y estado editable."""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from apps.audit.models import record
from apps.sales.models import EDITABLE_STATUSES, Order
from apps.sales.selectors import scoped_orders
from apps.tenancy.models import Membership

_CENTS = Decimal("0.01")
_ZERO = Decimal("0")

NOT_EDITABLE = "La comanda no se puede modificar en su estado actual."


def _money(value) -> str:
    return str(Decimal(value).quantize(_CENTS))


def _order_snapshot(order: Order) -> dict:
    return {
        "number": order.number,
        "status": order.status,
        "payment_status": order.payment_status,
        "client": str(order.client.public_id) if order.client_id else None,
        "barber": str(order.barber.public_id) if order.barber_id else None,
        "subtotal": _money(order.subtotal),
        "discount": _money(order.discount),
        "discount_reason": order.discount_reason,
        "total": _money(order.total),
        "amount_paid": _money(order.amount_paid),
        "commission_total": _money(order.commission_total),
    }


def _audit(actor: Membership, action: str, *, order: Order, before: dict | None, after: dict) -> None:
    record(
        action=action,
        entity=order._meta.label,
        entity_id=str(order.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        branch=order.branch,
        before=before,
        after=after,
    )


def _stock_reference(order: Order) -> str:
    return f"order:{order.public_id}"


def _locked_order(membership: Membership, public_id: UUID | str) -> Order:
    return scoped_orders(membership).select_for_update().get(public_id=public_id)


def _require_editable(order: Order) -> None:
    """Regla 3: solo comandas abiertas o en espera."""
    if order.status not in EDITABLE_STATUSES:
        raise ValidationError(NOT_EDITABLE, code="not_editable")


def _recalculate(order: Order) -> None:
    """Subtotal desde las líneas; la base rechaza un descuento que quede por encima."""
    order.subtotal = order.items.aggregate(
        total=Coalesce(Sum("line_total"), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2))
    )["total"]
    order.total = order.subtotal - order.discount
    order.full_clean()
    order.save()
