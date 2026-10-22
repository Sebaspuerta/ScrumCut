"""Comanda abierta: crear, agregar y editar líneas, descuento y espera.

Reglas 1–10. Defectos corregidos: 5 (descuento con límites y motivo), 6 (alcance
del Barbero), 7 y 8 (precio y tipo siempre del catálogo) y 9 (estados). Decisión 4.
Fase S4a de docs/sedes.md: toda escritura es sobre una comanda de la sede del alcance,
el barbero trabaja en esa sede y el precio es el vigente en ella.
"""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.branch_prices import current_price
from apps.catalog.models import Service
from apps.clients.models import Client
from apps.inventory.models import Product
from apps.sales.models import ItemType, Order, OrderItem, OrderStatus
from apps.sales.selectors import own_barber
from apps.sales.services._shared import (
    NOT_EDITABLE,
    _audit,
    _locked_order,
    _order_snapshot,
    _recalculate,
    _require_editable,
)
from apps.staff.models import Barber
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import BarbershopSettings, Branch, Membership
from apps.tenancy.permissions import ensure_permission
from apps.tenancy.roles import Role

BARBER_OTHER_BRANCH = "El barbero no trabaja en esta sede."


def _get_or_invalid(queryset, field: str, *, message: str, **lookup):
    try:
        return queryset.get(**lookup)
    except queryset.model.DoesNotExist as exc:
        raise ValidationError({field: message}) from exc


def _active_barber(public_id: UUID | str, *, branch: Branch) -> Barber:
    """Activo, vivo y que trabaje en la sede de la comanda (BarberBranch, decisión 18)."""
    barber = _get_or_invalid(
        Barber.objects,
        "barber",
        message="El barbero no existe o está inactivo.",
        public_id=public_id,
        deleted_at__isnull=True,
        is_active=True,
    )
    if not barber.branch_links.filter(branch=branch).exists():
        raise ValidationError({"barber": BARBER_OTHER_BRANCH})
    return barber


def _order_client(public_id: UUID | str | None) -> Client | None:
    if public_id is None:
        return None
    return _get_or_invalid(
        Client.objects,
        "client",
        message="El cliente no existe.",
        public_id=public_id,
        deleted_at__isnull=True,
        anonymized_at__isnull=True,
    )


def _order_barber(membership: Membership, public_id: UUID | str | None, *, branch: Branch) -> Barber | None:
    """El barbero elegido; si no se eligió y quien crea es Barbero, él mismo."""
    if public_id is not None:
        return _active_barber(public_id, branch=branch)
    return own_barber(membership) if membership.role == Role.BARBER else None


def create_order(
    membership: Membership,
    scope: BranchScope,
    *,
    client: UUID | str | None = None,
    barber: UUID | str | None = None,
) -> Order:
    """En la sede del alcance. El número sale del consecutivo de la barbería, bloqueado para que no se repita."""
    ensure_permission(membership, "comandas.crear")
    target_branch = scope.branch_for_write(membership)
    target_client = _order_client(client)
    target_barber = _order_barber(membership, barber, branch=target_branch)
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
        _audit(membership, "comanda.crear", order=order, before=None, after=_order_snapshot(order))
    return order


def change_order_client(
    membership: Membership, order: UUID | str, *, scope: BranchScope, client: UUID | str | None
) -> Order:
    """Cambia el cliente de una comanda abierta o en espera de la sede del alcance; None la deja de mostrador.

    El cliente debe ser de esta barbería (el manager ya filtra por ella). Queda en la auditoría con
    el antes y el después. Sin cliente, la comanda ya no puede cerrarse como fiado (`close_order`).
    """
    ensure_permission(membership, "comandas.editar")
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
        _require_editable(locked)
        before = _order_snapshot(locked)
        locked.client = _order_client(client)
        locked.save(update_fields=["client", "updated_at"])
        _audit(membership, "comanda.cambiar_cliente", order=locked, before=before, after=_order_snapshot(locked))
    return locked


def _check_new_item(service: UUID | str | None, product: UUID | str | None, *, quantity: int) -> None:
    if (service is None) == (product is None):
        raise ValidationError("Indica un servicio o un producto.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError({"quantity": "La cantidad debe ser un entero mayor que cero."})


def _fill_service(item: OrderItem, public_id: UUID | str, *, barber: UUID | str | None) -> None:
    order = item.order
    catalog_service = _get_or_invalid(
        Service.objects,
        "service",
        message="El servicio no existe o está inactivo.",
        public_id=public_id,
        deleted_at__isnull=True,
        is_active=True,
    )
    item.item_type = ItemType.SERVICE
    item.service = catalog_service
    item.name = catalog_service.name
    item.unit_price = current_price(catalog_service, order.branch)
    item.barber = _active_barber(barber, branch=order.branch) if barber is not None else order.barber


def _fill_product(item: OrderItem, public_id: UUID | str) -> None:
    catalog_product = _get_or_invalid(
        Product.objects,
        "product",
        message="El producto no existe o está inactivo.",
        public_id=public_id,
        deleted_at__isnull=True,
        is_active=True,
    )
    item.item_type = ItemType.PRODUCT
    item.product = catalog_product
    item.name = catalog_product.name
    item.unit_price = current_price(catalog_product, item.order.branch)


def _save_line(item: OrderItem) -> None:
    item.line_total = item.unit_price * item.quantity
    item.full_clean()
    item.save()


def add_item(
    membership: Membership,
    order: UUID | str,
    *,
    scope: BranchScope,
    service: UUID | str | None = None,
    product: UUID | str | None = None,
    quantity: int = 1,
    barber: UUID | str | None = None,
) -> OrderItem:
    """Reglas 4–6 con los defectos 7 y 8 corregidos: el precio y el tipo salen siempre del
    catálogo, con el precio vigente en la sede de la comanda (decisión 17). No hay parámetro
    de precio: un precio enviado por el cliente no tiene por dónde entrar.
    """
    ensure_permission(membership, "comandas.editar")
    _check_new_item(service, product, quantity=quantity)
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
        _require_editable(locked)
        item = OrderItem(barbershop_id=locked.barbershop_id, order=locked, quantity=quantity)
        if service is not None:
            _fill_service(item, service, barber=barber)
        else:
            _fill_product(item, product)
        _save_line(item)
        before = _order_snapshot(locked)
        _recalculate(locked)
        after = {**_order_snapshot(locked), "item": item.name}
        _audit(membership, "comanda.agregar_item", order=locked, before=before, after=after)
    return item


def update_item_quantity(
    membership: Membership, order: UUID | str, *, scope: BranchScope, item: UUID | str, quantity: int
) -> OrderItem:
    ensure_permission(membership, "comandas.editar")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError({"quantity": "La cantidad debe ser un entero mayor que cero."})
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
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
            order=locked,
            before=before,
            after={**_order_snapshot(locked), "item": line.name},
        )
    return line


def remove_item(membership: Membership, order: UUID | str, *, scope: BranchScope, item: UUID | str) -> None:
    """Una línea de una comanda abierta es borrador: se borra físicamente y queda en la auditoría."""
    ensure_permission(membership, "comandas.editar")
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
        _require_editable(locked)
        line = locked.items.get(public_id=item)
        before = _order_snapshot(locked)
        name = line.name
        line.delete()
        _recalculate(locked)
        _audit(
            membership,
            "comanda.quitar_item",
            order=locked,
            before=before,
            after={**_order_snapshot(locked), "item": name},
        )


def set_discount(
    membership: Membership, order: UUID | str, *, scope: BranchScope, amount: Decimal, reason: str = ""
) -> Order:
    """Descuento entre 0 y el subtotal, con motivo si es mayor que cero (defecto 5).

    Una cortesía es un descuento igual al subtotal con su motivo (decisión 4).
    """
    ensure_permission(membership, "comandas.descontar")
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
        _require_editable(locked)
        before = _order_snapshot(locked)
        locked.discount = Decimal(amount)
        locked.discount_reason = (reason or "").strip() if locked.discount else ""
        locked.total = locked.subtotal - locked.discount
        locked.full_clean()
        locked.save(update_fields=["discount", "discount_reason", "total", "updated_at"])
        _audit(membership, "comanda.descontar", order=locked, before=before, after=_order_snapshot(locked))
    return locked


def _move(
    membership: Membership, order: UUID | str, *, scope: BranchScope, source: str, target: str, action: str
) -> Order:
    ensure_permission(membership, "comandas.editar")
    with transaction.atomic():
        locked = _locked_order(membership, order, scope=scope)
        if locked.status != source:
            raise ValidationError(NOT_EDITABLE, code="not_editable")
        before = _order_snapshot(locked)
        locked.status = target
        locked.save(update_fields=["status", "updated_at"])
        _audit(membership, action, order=locked, before=before, after=_order_snapshot(locked))
    return locked


def hold_order(membership: Membership, order: UUID | str, *, scope: BranchScope) -> Order:
    """Regla 10 con el defecto 9 corregido: solo una comanda abierta pasa a espera."""
    return _move(
        membership, order, scope=scope, source=OrderStatus.OPEN, target=OrderStatus.ON_HOLD, action="comanda.en_espera"
    )


def resume_order(membership: Membership, order: UUID | str, *, scope: BranchScope) -> Order:
    return _move(
        membership, order, scope=scope, source=OrderStatus.ON_HOLD, target=OrderStatus.OPEN, action="comanda.reanudar"
    )
