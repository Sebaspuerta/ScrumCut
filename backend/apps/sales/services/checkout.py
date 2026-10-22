"""Cobro desde la pantalla de Comandas (fase F3): efectivo con vueltas, transferencia o fiado.

Las vueltas se calculan aquí, en el servidor; el JavaScript de la pantalla solo muestra una vista previa.
El cierre es `close_order`: bloquea la comanda, así que un segundo envío del mismo cobro encuentra la
comanda ya cerrada y no cobra dos veces.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cash.choices import PaymentMethod
from apps.sales.models import Order
from apps.sales.services._shared import _locked_order
from apps.sales.services.closing import close_order
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

CREDIT = "fiado"


@dataclass(frozen=True)
class Checkout:
    method: str
    received: Decimal | None = None
    reference: str = ""
    due_date: date | None = None


def cash_change(total: Decimal, received: Decimal) -> Decimal:
    """Lo que se le devuelve al cliente; si recibió menos que el total, el cobro no se hace."""
    if received < total:
        raise ValidationError(
            {"recibido": "Lo recibido no alcanza para el total de la comanda."}, code="not_enough_cash"
        )
    return received - total


def _payments(order: Order, checkout: Checkout) -> tuple[list[dict], bool]:
    """Los pagos y si queda como fiado. En efectivo se registra el total, no lo recibido."""
    if checkout.method == CREDIT:
        return [], True
    if not order.total:
        return [], False
    return [{"method": checkout.method, "amount": order.total, "reference": checkout.reference}], False


def checkout_order(
    membership: Membership, order: UUID | str, *, scope: BranchScope, checkout: Checkout
) -> tuple[Order, Decimal]:
    """Cobra la comanda completa o la deja como fiado (con cliente, lo exige `close_order`).

    Devuelve la comanda cerrada y las vueltas (0 si no fue en efectivo).
    """
    ensure_permission(membership, "comandas.cerrar")
    with transaction.atomic():
        current = _locked_order(membership, order, scope=scope)
        change = Decimal("0.00")
        if checkout.method == PaymentMethod.CASH:
            change = cash_change(current.total, checkout.received or Decimal("0"))
        payments, as_credit = _payments(current, checkout)
        closed = close_order(
            membership,
            current.public_id,
            scope=scope,
            payments=payments,
            as_credit=as_credit,
            due_date=checkout.due_date,
        )
    return closed, change
