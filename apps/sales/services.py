"""Escrituras de comandas.

Reglas portadas de MAGNUS v1 (`order_service.py`, `payment_service.py`), numeradas
como en `docs/migracion-magnus.md`: 1–20. Defectos corregidos: 1 (se copia la
comisión al cerrar), 2 (y el costo), 5 (descuento con límites y motivo), 6
(alcance del Barbero), 7 y 8 (precio y tipo siempre del catálogo), 9 (estados),
10 (cierre con bloqueo), 11 (sin saldo huérfano), 12 (anulación con reversos),
13 (sin `str(e)`), 22 (pagos ≤ total). Decisiones 3, 4 y 6.

Igual que en las demás apps: un objeto inexistente, de otra barbería o fuera del
alcance del rol lanza `DoesNotExist`; los datos inválidos, `ValidationError`.
"""

from collections.abc import Iterable
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.audit.models import record
from apps.cash.models import Direction, MovementKind
from apps.cash.selectors import open_session_for
from apps.cash.services import record_money
from apps.catalog.models import Service
from apps.clients.models import Client
from apps.inventory.models import MovementType, Product, StockMovement
from apps.inventory.selectors import consumables_for
from apps.inventory.services import apply_stock_movement
from apps.receivables import services as receivables
from apps.sales.models import EDITABLE_STATUSES, ItemType, Order, OrderItem, OrderStatus, Payment, PaymentStatus
from apps.sales.selectors import own_barber, scoped_orders
from apps.staff.models import Barber, CommissionType
from apps.staff.selectors import resolve_commission
from apps.tenancy.models import BarbershopSettings, Branch, Membership
from apps.tenancy.permissions import ensure_member, ensure_permission
from apps.tenancy.roles import Role

_CENTS = Decimal("0.01")
_ZERO = Decimal("0")

NOT_EDITABLE = "La comanda no se puede modificar en su estado actual."
_PAYMENT_KEYS = {"method", "amount", "reference"}


# ── Apoyo ────────────────────────────────────────────────────────────────────


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


def _audit(actor: Membership, action: str, order: Order, *, before: dict | None, after: dict) -> None:
    record(
        action=action,
        entity=order._meta.label,
        entity_id=str(order.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
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


def _get_or_invalid(queryset, field: str, message: str, **lookup):
    try:
        return queryset.get(**lookup)
    except queryset.model.DoesNotExist as exc:
        raise ValidationError({field: message}) from exc


def _active_barber(public_id: UUID | str) -> Barber:
    return _get_or_invalid(
        Barber.objects,
        "barber",
        "El barbero no existe o está inactivo.",
        public_id=public_id,
        deleted_at__isnull=True,
        is_active=True,
    )


def _recalculate(order: Order) -> None:
    """Subtotal desde las líneas; la base rechaza un descuento que quede por encima."""
    order.subtotal = order.items.aggregate(
        total=Coalesce(Sum("line_total"), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2))
    )["total"]
    order.total = order.subtotal - order.discount
    order.full_clean()
    order.save()


# ── Comanda abierta ──────────────────────────────────────────────────────────


def create_order(
    membership: Membership,
    branch: UUID | str,
    *,
    client: UUID | str | None = None,
    barber: UUID | str | None = None,
) -> Order:
    """El número sale del consecutivo de la barbería, bloqueado para que no se repita."""
    ensure_permission(membership, "comandas.crear")
    target_branch = _get_or_invalid(Branch.objects, "branch", "La sede no existe.", public_id=branch, is_active=True)
    target_client = None
    if client is not None:
        target_client = _get_or_invalid(
            Client.objects,
            "client",
            "El cliente no existe.",
            public_id=client,
            deleted_at__isnull=True,
            anonymized_at__isnull=True,
        )
    if barber is not None:
        target_barber = _active_barber(barber)
    elif membership.role == Role.BARBER:
        target_barber = own_barber(membership)
    else:
        target_barber = None
    with transaction.atomic():
        settings = BarbershopSettings.objects.select_for_update().get()
        number = settings.next_order_number
        settings.next_order_number = number + 1
        settings.save(update_fields=["next_order_number", "updated_at"])
        order = Order(
            barbershop_id=membership.barbershop_id,
            number=number,
            branch=target_branch,
            client=target_client,
            barber=target_barber,
            created_by=membership.user,
        )
        order.full_clean()
        order.save()
        _audit(membership, "comanda.crear", order, before=None, after=_order_snapshot(order))
    return order


def add_item(
    membership: Membership,
    order: UUID | str,
    *,
    service: UUID | str | None = None,
    product: UUID | str | None = None,
    quantity: int = 1,
    barber: UUID | str | None = None,
) -> OrderItem:
    """Reglas 4–6 con los defectos 7 y 8 corregidos: el precio y el tipo salen siempre del
    catálogo. No hay parámetro de precio: un precio enviado por el cliente no tiene por dónde entrar.
    """
    ensure_permission(membership, "comandas.editar")
    if (service is None) == (product is None):
        raise ValidationError("Indica un servicio o un producto.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError({"quantity": "La cantidad debe ser un entero mayor que cero."})
    with transaction.atomic():
        locked = _locked_order(membership, order)
        _require_editable(locked)
        item = OrderItem(barbershop_id=locked.barbershop_id, order=locked, quantity=quantity)
        if service is not None:
            catalog_service = _get_or_invalid(
                Service.objects,
                "service",
                "El servicio no existe o está inactivo.",
                public_id=service,
                deleted_at__isnull=True,
                is_active=True,
            )
            item.item_type = ItemType.SERVICE
            item.service = catalog_service
            item.name = catalog_service.name
            item.unit_price = catalog_service.price
            item.barber = _active_barber(barber) if barber is not None else locked.barber
        else:
            catalog_product = _get_or_invalid(
                Product.objects,
                "product",
                "El producto no existe o está inactivo.",
                public_id=product,
                deleted_at__isnull=True,
                is_active=True,
            )
            item.item_type = ItemType.PRODUCT
            item.product = catalog_product
            item.name = catalog_product.name
            item.unit_price = catalog_product.sale_price
        item.line_total = item.unit_price * quantity
        item.full_clean()
        item.save()
        before = _order_snapshot(locked)
        _recalculate(locked)
        _audit(
            membership,
            "comanda.agregar_item",
            locked,
            before=before,
            after={**_order_snapshot(locked), "item": item.name},
        )
    return item


def update_item_quantity(membership: Membership, order: UUID | str, item: UUID | str, quantity: int) -> OrderItem:
    ensure_permission(membership, "comandas.editar")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError({"quantity": "La cantidad debe ser un entero mayor que cero."})
    with transaction.atomic():
        locked = _locked_order(membership, order)
        _require_editable(locked)
        line = locked.items.get(public_id=item)
        before = _order_snapshot(locked)
        line.quantity = quantity
        line.line_total = line.unit_price * quantity
        line.full_clean()
        line.save(update_fields=["quantity", "line_total", "updated_at"])
        _recalculate(locked)
        _audit(
            membership,
            "comanda.editar_item",
            locked,
            before=before,
            after={**_order_snapshot(locked), "item": line.name},
        )
    return line


def remove_item(membership: Membership, order: UUID | str, item: UUID | str) -> None:
    """Una línea de una comanda abierta es borrador: se borra físicamente y queda en la auditoría."""
    ensure_permission(membership, "comandas.editar")
    with transaction.atomic():
        locked = _locked_order(membership, order)
        _require_editable(locked)
        line = locked.items.get(public_id=item)
        before = _order_snapshot(locked)
        name = line.name
        line.delete()
        _recalculate(locked)
        _audit(
            membership, "comanda.quitar_item", locked, before=before, after={**_order_snapshot(locked), "item": name}
        )


def set_discount(membership: Membership, order: UUID | str, amount: Decimal, reason: str = "") -> Order:
    """Descuento entre 0 y el subtotal, con motivo si es mayor que cero (defecto 5).

    Una cortesía es un descuento igual al subtotal con su motivo (decisión 4).
    """
    ensure_permission(membership, "comandas.descontar")
    with transaction.atomic():
        locked = _locked_order(membership, order)
        _require_editable(locked)
        before = _order_snapshot(locked)
        locked.discount = Decimal(amount)
        locked.discount_reason = (reason or "").strip() if locked.discount else ""
        locked.total = locked.subtotal - locked.discount
        locked.full_clean()
        locked.save(update_fields=["discount", "discount_reason", "total", "updated_at"])
        _audit(membership, "comanda.descontar", locked, before=before, after=_order_snapshot(locked))
    return locked


def _move(membership: Membership, order: UUID | str, *, source: str, target: str, action: str) -> Order:
    ensure_permission(membership, "comandas.editar")
    with transaction.atomic():
        locked = _locked_order(membership, order)
        if locked.status != source:
            raise ValidationError(NOT_EDITABLE, code="not_editable")
        before = _order_snapshot(locked)
        locked.status = target
        locked.save(update_fields=["status", "updated_at"])
        _audit(membership, action, locked, before=before, after=_order_snapshot(locked))
    return locked


def hold_order(membership: Membership, order: UUID | str) -> Order:
    """Regla 10 con el defecto 9 corregido: solo una comanda abierta pasa a espera."""
    return _move(membership, order, source=OrderStatus.OPEN, target=OrderStatus.ON_HOLD, action="comanda.en_espera")


def resume_order(membership: Membership, order: UUID | str) -> Order:
    return _move(membership, order, source=OrderStatus.ON_HOLD, target=OrderStatus.OPEN, action="comanda.reanudar")


# ── Cierre ───────────────────────────────────────────────────────────────────


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


def _close_locked(
    membership: Membership, order: Order, payments: list[dict], *, as_credit: bool, due_date: date | None
) -> Order:
    _require_editable(order)
    lines = list(order.items.select_related("service", "product", "barber").order_by("pk"))
    if not lines:
        raise ValidationError("La comanda no tiene ítems.", code="empty_order")
    for line in lines:
        if line.item_type == ItemType.SERVICE:
            barber = line.barber or order.barber
            if barber is None or barber.is_deleted or not barber.is_active:
                raise ValidationError(
                    "Cada servicio necesita un barbero activo: %(name)s no lo tiene.",
                    code="missing_barber",
                    params={"name": line.name},
                )
            line.barber = barber

    _recalculate(order)
    paid = sum((payment["amount"] for payment in payments), _ZERO)
    if paid > order.total:
        raise ValidationError("Los pagos superan el total de la comanda.", code="overpaid")
    balance = order.total - paid
    if balance > 0 and not as_credit:
        raise ValidationError("La comanda tiene saldo: cóbrala completa o ciérrala como fiado.", code="unpaid_balance")
    if balance > 0 and order.client_id is None:
        raise ValidationError("Un fiado necesita un cliente.", code="credit_without_client")

    now = timezone.now()
    reference = _stock_reference(order)
    reason = f"Comanda #{order.number}"
    for line, share in zip(lines, _distribute_discount(lines, order.discount), strict=True):
        line.line_discount = share
        if line.item_type == ItemType.PRODUCT:
            line.name = line.product.name
            movement = apply_stock_movement(
                line.product, -line.quantity, MovementType.SALE, reason, membership, reference=reference
            )
            line.unit_cost = movement.unit_cost
            line.commission_type, line.commission_rate, line.commission_amount = "", None, _ZERO
        else:
            line.name = line.service.name
            consumables_cost = _ZERO
            for consumable in consumables_for(line.service):
                used = consumable.quantity * line.quantity
                movement = apply_stock_movement(
                    consumable.product, -used, MovementType.SERVICE, reason, membership, reference=reference
                )
                consumables_cost += movement.unit_cost * used
            line.unit_cost = _ZERO
            line.consumables_cost = consumables_cost
            _commission(line, now)
        line.full_clean()
        line.save()

    if payments:
        session = open_session_for(order.branch)
        if session is None:
            raise ValidationError("No hay una caja abierta en esta sede para recibir el pago.", code="no_open_session")
        for payment in payments:
            movement = record_money(
                session, MovementKind.SALE, Direction.IN, payment["method"], payment["amount"], reason, membership
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

    order.amount_paid = paid
    order.commission_total = sum((line.commission_amount for line in lines), _ZERO)
    if balance > 0:
        receivables.create_from_order(order, balance, membership, due_date)
        order.payment_status = PaymentStatus.CREDIT
    else:
        order.payment_status = PaymentStatus.PAID
    order.status = OrderStatus.CLOSED
    order.closed_at = now
    order.closed_by = membership.user
    order.full_clean()
    order.save()
    return order


def close_order(
    membership: Membership,
    order: UUID | str,
    payments: Iterable[dict] = (),
    *,
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
        locked = _locked_order(membership, order)
        before = _order_snapshot(locked)
        _close_locked(membership, locked, cleaned, as_credit=as_credit, due_date=due_date)
        _audit(membership, "comanda.cerrar", locked, before=before, after=_order_snapshot(locked))
    return locked


def quick_register(
    membership: Membership,
    branch: UUID | str,
    barber: UUID | str,
    method: str,
    *,
    service: UUID | str | None = None,
    product: UUID | str | None = None,
    quantity: int = 1,
    reference: str = "",
) -> Order:
    """Regla 17: un corte o un producto, cobrado completo, en una sola transacción."""
    ensure_permission(membership, "comandas.cerrar")
    with transaction.atomic():
        order = create_order(membership, branch, barber=barber)
        add_item(membership, order.public_id, service=service, product=product, quantity=quantity)
        order.refresh_from_db()
        payments = [{"method": method, "amount": order.total, "reference": reference}] if order.total else []
        return close_order(membership, order.public_id, payments)


# ── Anulación ────────────────────────────────────────────────────────────────


def cancel_order(membership: Membership, order: UUID | str, reason: str) -> Order:
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
            _reverse_closed(membership, locked, reason)
        else:
            raise ValidationError("La comanda ya está anulada.", code="already_cancelled")
        locked.status = OrderStatus.CANCELLED
        locked.cancelled_at = timezone.now()
        locked.cancelled_by = membership.user
        locked.cancel_reason = reason
        locked.full_clean()
        locked.save()
        _audit(membership, "comanda.anular", locked, before=before, after={**_order_snapshot(locked), "reason": reason})
    return locked


def _reverse_closed(membership: Membership, order: Order, reason: str) -> None:
    receivables.cancel_for_order(order, membership, reason)

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
                Direction.OUT,
                payment.method,
                payment.amount,
                f"Devolución comanda #{order.number}",
                membership,
            )

    reference = _stock_reference(order)
    sold = StockMovement.objects.filter(
        reference=reference, movement_type__in=(MovementType.SALE, MovementType.SERVICE)
    ).select_related("product")
    for movement in sold.order_by("pk"):
        apply_stock_movement(
            movement.product,
            -movement.quantity,
            MovementType.REVERSAL,
            f"Anulación comanda #{order.number}",
            membership,
            unit_cost=movement.unit_cost,
            reference=reference,
        )
