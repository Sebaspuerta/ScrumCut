"""Cobro rápido (regla 17): crea, agrega y cierra una comanda en una sola transacción.

Con llave (`quick_register_once`, la app de React): el diálogo manda la misma llave en cada reintento de un
cobro, así que un doble envío o un reintento de red devuelve la comanda ya cobrada en vez de cobrar otra. Entre
dos envíos simultáneos decide la restricción única de la base (`uq_order_request_key_per_barbershop`).
"""

from uuid import UUID

from django.db import IntegrityError, transaction

from apps.sales.models import ItemType, Order
from apps.sales.services.closing import close_order
from apps.sales.services.open_orders import add_item, create_order
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


class QuickChargeConflictError(Exception):
    """La llave ya cobró otra cosa: otro barbero, ítem o forma de pago, o lo cobró otra persona u otra sede."""


def quick_register(
    membership: Membership,
    scope: BranchScope,
    *,
    barber: UUID | str,
    method: str,
    service: UUID | str | None = None,
    product: UUID | str | None = None,
    quantity: int = 1,
    reference: str = "",
    request_key: UUID | None = None,
) -> Order:
    """Regla 17: un corte o un producto, cobrado completo, en una sola transacción."""
    ensure_permission(membership, "comandas.cerrar")
    with transaction.atomic():
        order = create_order(membership, scope, barber=barber, request_key=request_key)
        add_item(membership, order.public_id, scope=scope, service=service, product=product, quantity=quantity)
        order.refresh_from_db()
        payments = [{"method": method, "amount": order.total, "reference": reference}] if order.total else []
        return close_order(membership, order.public_id, scope=scope, payments=payments)


def _charged_with(request_key: UUID) -> Order | None:
    return (
        Order.objects.filter(request_key=request_key)
        .select_related("barber")
        .prefetch_related("items__service", "items__product", "payments")
        .first()
    )


def _same_charge(
    order: Order,
    membership: Membership,
    *,
    scope: BranchScope,
    barber: UUID | str,
    method: str,
    service: UUID | str | None,
    product: UUID | str | None,
) -> bool:
    """La misma persona, en la misma sede, con el mismo barbero, ítem y forma de pago (sin pago si costó 0)."""
    line = order.items.all()[0]
    item = line.service if line.item_type == ItemType.SERVICE else line.product
    requested = (ItemType.SERVICE, str(service)) if service is not None else (ItemType.PRODUCT, str(product))
    return (
        order.created_by_id == membership.user_id
        and scope.branch is not None
        and order.branch_id == scope.branch.pk
        and order.barber is not None
        and str(order.barber.public_id) == str(barber)
        and (line.item_type, str(item.public_id)) == requested
        and {payment.method for payment in order.payments.all()} <= {method}
    )


def quick_register_once(
    membership: Membership,
    scope: BranchScope,
    *,
    request_key: UUID,
    barber: UUID | str,
    method: str,
    service: UUID | str | None = None,
    product: UUID | str | None = None,
    reference: str = "",
) -> tuple[Order, bool]:
    """El cobro rápido de una llave: la comanda y si se cobró ahora (False: ya estaba cobrada con esa llave).

    Una llave ya usada con otros datos lanza `QuickChargeConflictError` y no cobra nada.
    """
    ensure_permission(membership, "comandas.cerrar")
    scope.branch_for_write(membership)  # en «todas» no se cobra, tampoco un reenvío
    charge = {"barber": barber, "method": method, "service": service, "product": product}
    try:
        with transaction.atomic():
            previous = _charged_with(request_key)
            if previous is None:
                return quick_register(membership, scope, **charge, reference=reference, request_key=request_key), True
    except IntegrityError:
        # Otro envío con la misma llave se cobró mientras este esperaba: la base rechazó el segundo.
        previous = _charged_with(request_key)
        if previous is None:
            raise
    if not _same_charge(previous, membership, scope=scope, **charge):
        raise QuickChargeConflictError
    return previous, False
