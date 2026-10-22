"""Cobro desde la pantalla de Comandas (fases F3 y F3b): una forma de pago o hasta tres combinadas.

Todo se valida aquí, en el servidor: la suma de las partes es exactamente el total, las vueltas existen
solo sobre la parte en efectivo y el fiado va como mucho en una parte (con cliente, lo exige
`close_order`). El JavaScript de la pantalla solo muestra una vista previa.
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
from apps.core.formatting import format_cop
from apps.sales.models import Order
from apps.sales.services._shared import _locked_order
from apps.sales.services.closing import close_order
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

CREDIT = "fiado"
MAX_PARTS = 3
_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class PaymentPart:
    """Una forma de pago y su monto. Sin monto, es el total de la comanda (una sola forma)."""

    method: str
    amount: Decimal | None = None
    reference: str = ""


@dataclass(frozen=True)
class Checkout:
    parts: tuple[PaymentPart, ...]
    received: Decimal | None = None  # el efectivo que entregó el cliente, si alguna parte es en efectivo
    due_date: date | None = None

    @classmethod
    def whole(cls, method: str, *, received: Decimal | None = None, reference: str = "", due_date=None) -> "Checkout":
        """Toda la comanda con una sola forma de pago."""
        return cls(parts=(PaymentPart(method, reference=reference),), received=received, due_date=due_date)


def cash_change(total: Decimal, received: Decimal) -> Decimal:
    """Lo que se le devuelve al cliente; si recibió menos que el efectivo a cobrar, el cobro no se hace."""
    if received < total:
        raise ValidationError({"recibido": "Lo recibido no alcanza para la parte en efectivo."}, code="not_enough_cash")
    return received - total


def _amounts(order: Order, checkout: Checkout) -> list[PaymentPart]:
    """Cada parte con su monto. Las partes deben sumar exactamente el total y el fiado ir una sola vez."""
    if not 1 <= len(checkout.parts) <= MAX_PARTS:
        raise ValidationError(f"El pago se divide en {MAX_PARTS} partes como máximo.", code="too_many_parts")
    if [part.method for part in checkout.parts].count(CREDIT) > 1:
        raise ValidationError("El fiado va en una sola parte.", code="credit_twice")
    parts = [
        PaymentPart(part.method, order.total if part.amount is None else part.amount, part.reference)
        for part in checkout.parts
    ]
    if sum((part.amount for part in parts), _ZERO) != order.total:
        raise ValidationError(
            "La suma de los pagos debe ser exactamente el total de la comanda (%(total)s).",
            code="parts_do_not_add_up",
            params={"total": format_cop(order.total)},
        )
    return parts


def _change(parts: list[PaymentPart], received: Decimal | None) -> Decimal:
    """Las vueltas solo existen sobre la parte en efectivo."""
    cash = sum((part.amount for part in parts if part.method == PaymentMethod.CASH), _ZERO)
    return cash_change(cash, received or _ZERO) if cash else _ZERO


def _payments(parts: list[PaymentPart]) -> tuple[list[dict], bool]:
    """Los pagos que entran a caja y si el resto queda como fiado."""
    payments = [
        {"method": part.method, "amount": part.amount, "reference": part.reference}
        for part in parts
        if part.method != CREDIT and part.amount
    ]
    return payments, any(part.method == CREDIT and part.amount for part in parts)


def checkout_order(
    membership: Membership, order: UUID | str, *, scope: BranchScope, checkout: Checkout
) -> tuple[Order, Decimal]:
    """Cobra la comanda con una forma de pago o con varias, y deja como fiado la parte que se fía.

    Devuelve la comanda cerrada y las vueltas (0 si no hubo efectivo).
    """
    ensure_permission(membership, "comandas.cerrar")
    with transaction.atomic():
        current = _locked_order(membership, order, scope=scope)
        parts = _amounts(current, checkout)
        change = _change(parts, checkout.received)
        payments, as_credit = _payments(parts)
        closed = close_order(
            membership,
            current.public_id,
            scope=scope,
            payments=payments,
            as_credit=as_credit,
            due_date=checkout.due_date,
        )
    return closed, change
