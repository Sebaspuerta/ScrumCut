"""Cobro rápido (regla 17): crea, agrega y cierra una comanda en una sola transacción."""

from uuid import UUID

from django.db import transaction

from apps.sales.models import Order
from apps.sales.services.closing import close_order
from apps.sales.services.open_orders import add_item, create_order
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


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
) -> Order:
    """Regla 17: un corte o un producto, cobrado completo, en una sola transacción."""
    ensure_permission(membership, "comandas.cerrar")
    with transaction.atomic():
        order = create_order(membership, scope, barber=barber)
        add_item(membership, order.public_id, service=service, product=product, quantity=quantity)
        order.refresh_from_db()
        payments = [{"method": method, "amount": order.total, "reference": reference}] if order.total else []
        return close_order(membership, order.public_id, payments=payments)
