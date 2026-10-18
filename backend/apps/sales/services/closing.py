"""Cierre de comanda: copia precio, costo y comisión a cada línea, cobra y deja el saldo como fiado.

Reglas 11–16. Defectos corregidos: 1 (se copia la comisión al cerrar), 2 (y el
costo), 10 (cierre con bloqueo), 11 (sin saldo huérfano) y 22 (pagos ≤ total).
Decisiones 3 y 6.
"""

from collections.abc import Iterable
from datetime import date, datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cash.models import Direction, MovementKind
from apps.cash.selectors import open_session_for
from apps.cash.services import record_money
from apps.inventory.models import MovementType
from apps.inventory.selectors import consumables_for
from apps.inventory.services import apply_stock_movement
from apps.receivables import services as receivables
from apps.sales.models import ItemType, Order, OrderItem, OrderStatus, Payment, PaymentStatus
from apps.sales.services._shared import (
    _CENTS,
    _ZERO,
    _audit,
    _locked_order,
    _order_snapshot,
    _recalculate,
    _require_editable,
    _stock_reference,
)
from apps.staff.models import CommissionType
from apps.staff.selectors import resolve_commission
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

_PAYMENT_KEYS = {"method", "amount", "reference"}


def _clean_payments(payments: Iterable[dict]) -> list[dict]:
    cleaned = []
    for payment in payments:
        unknown = set(payment) - _PAYMENT_KEYS
        if unknown:
            raise TypeError(f"Campos de pago desconocidos: {sorted(unknown)}")
        amount = Decimal(str(payment["amount"]))
        if amount <= 0:
            raise ValidationError({"payments": "Cada pago debe ser mayor que cero."})
        cleaned.append(
            {"method": payment["method"], "amount": amount, "reference": (payment.get("reference") or "").strip()}
        )
    return cleaned


def _distribute_discount(lines: list[OrderItem], discount: Decimal) -> list[Decimal]:
    """Decisión 3: descuento repartido en proporción al total de cada línea; el residuo
    del redondeo va a la línea más grande (la primera, si hay empate)."""
    subtotal = sum((line.line_total for line in lines), _ZERO)
    if not discount or not subtotal:
        return [_ZERO for _ in lines]
    shares = [(discount * line.line_total / subtotal).quantize(_CENTS, rounding=ROUND_DOWN) for line in lines]
    largest = max(range(len(lines)), key=lambda index: (lines[index].line_total, -index))
    shares[largest] += discount - sum(shares, _ZERO)
    return shares


def _commission(line: OrderItem, now) -> None:
    """Comisión solo en servicios: porcentaje sobre el neto de la línea; fijo por unidad."""
    commission_type, rate = resolve_commission(line.barber, line.service, now)
    if commission_type == CommissionType.PERCENTAGE:
        amount = (line.line_total - line.line_discount) * rate / 100
    else:
        amount = rate * line.quantity
    line.commission_type = commission_type
    line.commission_rate = rate
    line.commission_amount = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _assign_service_barbers(order: Order, lines: list[OrderItem]) -> None:
    for line in lines:
        if line.item_type != ItemType.SERVICE:
            continue
        barber = line.barber or order.barber
        if barber is None or barber.is_deleted or not barber.is_active:
            raise ValidationError(
                "Cada servicio necesita un barbero activo: %(name)s no lo tiene.",
                code="missing_barber",
                params={"name": line.name},
            )
        line.barber = barber


def _validated_balance(order: Order, payments: list[dict], *, as_credit: bool) -> tuple[Decimal, Decimal]:
    """Lo pagado y el saldo. Un saldo solo se acepta como fiado y con cliente."""
    paid = sum((payment["amount"] for payment in payments), _ZERO)
    if paid > order.total:
        raise ValidationError("Los pagos superan el total de la comanda.", code="overpaid")
    balance = order.total - paid
    if balance > 0 and not as_credit:
        raise ValidationError("La comanda tiene saldo: cóbrala completa o ciérrala como fiado.", code="unpaid_balance")
    if balance > 0 and order.client_id is None:
        raise ValidationError("Un fiado necesita un cliente.", code="credit_without_client")
    return paid, balance


def _settle_product_line(line: OrderItem, membership: Membership, *, reason: str, reference: str) -> None:
    """El costo copiado es el del movimiento de stock; un producto no lleva comisión."""
    line.name = line.product.name
    movement = apply_stock_movement(
        line.product,
        -line.quantity,
        branch=line.order.branch,  # el consumo sale de la sede de la comanda (decisión 6)
        movement_type=MovementType.SALE,
        reason=reason,
        actor=membership,
        reference=reference,
    )
    line.unit_cost = movement.unit_cost
    line.commission_type, line.commission_rate, line.commission_amount = "", None, _ZERO


def _settle_service_line(
    line: OrderItem, membership: Membership, *, reason: str, reference: str, now: datetime
) -> None:
    """El costo de un servicio es el de sus insumos, que se descuentan del stock."""
    line.name = line.service.name
    consumables_cost = _ZERO
    for consumable in consumables_for(line.service):
        used = consumable.quantity * line.quantity
        movement = apply_stock_movement(
            consumable.product,
            -used,
            branch=line.order.branch,
            movement_type=MovementType.SERVICE,
            reason=reason,
            actor=membership,
            reference=reference,
        )
        consumables_cost += movement.unit_cost * used
    line.unit_cost = _ZERO
    line.consumables_cost = consumables_cost
    _commission(line, now)


def _record_sale_payments(order: Order, payments: list[dict], *, membership: Membership, reason: str) -> None:
    if not payments:
        return
    session = open_session_for(order.branch)
    if session is None:
        raise ValidationError("No hay una caja abierta en esta sede para recibir el pago.", code="no_open_session")
    for payment in payments:
        movement = record_money(
            session,
            MovementKind.SALE,
            direction=Direction.IN,
            method=payment["method"],
            amount=payment["amount"],
            description=reason,
            actor=membership,
        )
        receipt = Payment(
            barbershop_id=order.barbershop_id,
            order=order,
            cash_movement=movement,
            method=payment["method"],
            amount=payment["amount"],
            reference=payment["reference"],
            received_by=membership.user,
        )
        receipt.full_clean()
        receipt.save()


def _mark_closed(
    order: Order,
    lines: list[OrderItem],
    *,
    membership: Membership,
    paid: Decimal,
    balance: Decimal,
    due_date: date | None,
    now: datetime,
) -> None:
    """El saldo que queda pasa a ser un fiado del cliente."""
    order.amount_paid = paid
    order.commission_total = sum((line.commission_amount for line in lines), _ZERO)
    if balance > 0:
        receivables.create_from_order(order, balance, actor=membership, due_date=due_date)
        order.payment_status = PaymentStatus.CREDIT
    else:
        order.payment_status = PaymentStatus.PAID
    order.status = OrderStatus.CLOSED
    order.closed_at = now
    order.closed_by = membership.user
    order.full_clean()
    order.save()


def _close_locked(
    membership: Membership, order: Order, *, payments: list[dict], as_credit: bool, due_date: date | None
) -> Order:
    _require_editable(order)
    lines = list(order.items.select_related("service", "product", "barber").order_by("pk"))
    if not lines:
        raise ValidationError("La comanda no tiene ítems.", code="empty_order")
    _assign_service_barbers(order, lines)
    _recalculate(order)
    paid, balance = _validated_balance(order, payments, as_credit=as_credit)

    now = timezone.now()
    reference = _stock_reference(order)
    reason = f"Comanda #{order.number}"
    for line, share in zip(lines, _distribute_discount(lines, order.discount), strict=True):
        line.line_discount = share
        if line.item_type == ItemType.PRODUCT:
            _settle_product_line(line, membership, reason=reason, reference=reference)
        else:
            _settle_service_line(line, membership, reason=reason, reference=reference, now=now)
        line.full_clean()
        line.save()

    _record_sale_payments(order, payments, membership=membership, reason=reason)
    _mark_closed(order, lines, membership=membership, paid=paid, balance=balance, due_date=due_date, now=now)
    return order


def close_order(
    membership: Membership,
    order: UUID | str,
    *,
    scope: BranchScope,
    payments: Iterable[dict] = (),
    as_credit: bool = False,
    due_date: date | None = None,
) -> Order:
    """Reglas 11–16. Todo en una transacción: si algo falla, no queda nada a medias.

    `payments` es una lista de `{"method", "amount", "reference"}`; varios pagos son
    un pago combinado. Con saldo, `as_credit=True` lo deja como fiado del cliente.
    """
    ensure_permission(membership, "comandas.cerrar")
    cleaned = _clean_payments(payments)
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
        before = _order_snapshot(locked)
        _close_locked(membership, locked, payments=cleaned, as_credit=as_credit, due_date=due_date)
        _audit(membership, "comanda.cerrar", order=locked, before=before, after=_order_snapshot(locked))
    return locked
