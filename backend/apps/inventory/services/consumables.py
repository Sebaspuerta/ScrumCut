"""Insumos de servicios (regla 40): qué productos gasta cada servicio."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import Service
from apps.inventory.models import Product, ServiceConsumable
from apps.inventory.services._shared import _audit, _save_validated
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def _consumable_snapshot(consumable: ServiceConsumable) -> dict:
    return {
        "service": str(consumable.service.public_id),
        "product": str(consumable.product.public_id),
        "quantity": consumable.quantity,
    }


def add_consumable(
    membership: Membership, service: UUID | str, *, product: UUID | str, quantity: int
) -> ServiceConsumable:
    """Servicio y producto activos y vivos; un solo registro por par; cantidad > 0."""
    ensure_permission(membership, "servicios.editar")
    try:
        target_service = Service.objects.get(public_id=service, deleted_at__isnull=True, is_active=True)
    except Service.DoesNotExist as exc:
        raise ValidationError({"service": "El servicio no existe o está inactivo."}) from exc
    try:
        target_product = Product.objects.get(public_id=product, deleted_at__isnull=True, is_active=True)
    except Product.DoesNotExist as exc:
        raise ValidationError({"product": "El producto no existe o está inactivo."}) from exc
    with transaction.atomic():
        consumable = ServiceConsumable(
            barbershop_id=membership.barbershop_id, service=target_service, product=target_product, quantity=quantity
        )
        _save_validated(consumable, "Ese producto ya es insumo del servicio.")
        _audit(membership, "insumo.crear", obj=consumable, before=None, after=_consumable_snapshot(consumable))
    return consumable


def update_consumable(membership: Membership, public_id: UUID | str, *, quantity: int) -> ServiceConsumable:
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        consumable = ServiceConsumable.objects.select_for_update().get(public_id=public_id)
        before = _consumable_snapshot(consumable)
        consumable.quantity = quantity
        consumable.full_clean()
        consumable.save(update_fields=["quantity", "updated_at"])
        _audit(membership, "insumo.editar", obj=consumable, before=before, after=_consumable_snapshot(consumable))
    return consumable


def remove_consumable(membership: Membership, public_id: UUID | str) -> None:
    """Borrado físico: es configuración, no historial. La auditoría guarda lo que había."""
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        consumable = ServiceConsumable.objects.select_for_update().get(public_id=public_id)
        _audit(membership, "insumo.eliminar", obj=consumable, before=_consumable_snapshot(consumable), after=None)
        consumable.delete()
