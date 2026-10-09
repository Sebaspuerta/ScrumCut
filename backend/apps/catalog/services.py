"""Escrituras del catálogo.

Reglas portadas de MAGNUS v1 (`services/service_service.py`), numeradas como en
`docs/migracion-magnus.md`: 38 (nombre único) y 39 (desactivar y borrado lógico).

Cada función recibe la `Membership` de quien actúa y valida su permiso aquí,
además del `require_permission` de la vista. Un objeto inexistente, de otra
barbería o ya borrado lanza `DoesNotExist` (la vista responde 404); los datos
inválidos lanzan `ValidationError`.
"""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import record
from apps.catalog.models import Service, ServiceCategory
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

_UNSET = object()
_CENTS = Decimal("0.01")

DUPLICATE_SERVICE = "Ya existe un servicio con ese nombre."
DUPLICATE_CATEGORY = "Ya existe una categoría con ese nombre."


def _save_validated(obj, duplicate_message: str) -> None:
    obj.full_clean()
    try:
        with transaction.atomic():
            obj.save()
    except IntegrityError as exc:
        # Dos solicitudes simultáneas pueden pasar full_clean con el mismo nombre: decide la base.
        raise ValidationError(duplicate_message) from exc


def _audit(membership: Membership, action: str, obj, *, before: dict | None, after: dict | None) -> None:
    record(
        action=action,
        entity=obj._meta.label,
        entity_id=str(obj.public_id),
        actor=membership.user,
        barbershop=membership.barbershop,
        before=before,
        after=after,
    )


def _service_snapshot(service: Service) -> dict:
    return {
        "name": service.name,
        "category": str(service.category.public_id) if service.category_id else None,
        "description": service.description,
        # Mismo formato que guarda la base, sin importar cómo llegó el valor.
        "price": str(service.price.quantize(_CENTS)),
        "duration_minutes": service.duration_minutes,
        "is_active": service.is_active,
        "deleted_at": service.deleted_at.isoformat() if service.deleted_at else None,
    }


def _category_snapshot(category: ServiceCategory) -> dict:
    return {
        "name": category.name,
        "deleted_at": category.deleted_at.isoformat() if category.deleted_at else None,
    }


def _live_service_for_update(public_id: UUID | str) -> Service:
    return Service.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


def _live_category_for_update(public_id: UUID | str) -> ServiceCategory:
    return ServiceCategory.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


def _resolve_category(public_id: UUID | str | None) -> ServiceCategory | None:
    # La validación de FK de Django no filtra por barbería: se busca con el manager filtrado.
    if public_id is None:
        return None
    try:
        return ServiceCategory.objects.get(public_id=public_id, deleted_at__isnull=True)
    except ServiceCategory.DoesNotExist as exc:
        raise ValidationError({"category": "La categoría no existe."}) from exc


# ── Servicios ────────────────────────────────────────────────────────────────


def create_service(
    membership: Membership,
    *,
    name: str,
    price,
    duration_minutes: int,
    category: UUID | str | None = None,
    description: str = "",
) -> Service:
    ensure_permission(membership, "servicios.crear")
    with transaction.atomic():
        service = Service(
            barbershop_id=membership.barbershop_id,
            name=name.strip(),
            price=price,
            duration_minutes=duration_minutes,
            category=_resolve_category(category),
            description=description.strip(),
        )
        _save_validated(service, DUPLICATE_SERVICE)
        _audit(membership, "servicio.crear", service, before=None, after=_service_snapshot(service))
    return service


def update_service(
    membership: Membership,
    public_id: UUID | str,
    *,
    name=_UNSET,
    price=_UNSET,
    duration_minutes=_UNSET,
    category=_UNSET,
    description=_UNSET,
) -> Service:
    """Solo cambia los campos recibidos. `category=None` deja el servicio sin categoría."""
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        service = _live_service_for_update(public_id)
        before = _service_snapshot(service)
        if name is not _UNSET:
            service.name = name.strip()
        if price is not _UNSET:
            service.price = price
        if duration_minutes is not _UNSET:
            service.duration_minutes = duration_minutes
        if category is not _UNSET:
            service.category = _resolve_category(category)
        if description is not _UNSET:
            service.description = description.strip()
        _save_validated(service, DUPLICATE_SERVICE)
        after = _service_snapshot(service)
        if after != before:
            _audit(membership, "servicio.editar", service, before=before, after=after)
    return service


def _set_service_active(membership: Membership, public_id: UUID | str, *, active: bool) -> Service:
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        service = _live_service_for_update(public_id)
        if service.is_active == active:
            return service
        before = _service_snapshot(service)
        service.is_active = active
        service.save(update_fields=["is_active", "updated_at"])
        action = "servicio.activar" if active else "servicio.desactivar"
        _audit(membership, action, service, before=before, after=_service_snapshot(service))
    return service


def deactivate_service(membership: Membership, public_id: UUID | str) -> Service:
    """Regla 39: un servicio desactivado no se ofrece, pero conserva su nombre reservado."""
    return _set_service_active(membership, public_id, active=False)


def activate_service(membership: Membership, public_id: UUID | str) -> Service:
    return _set_service_active(membership, public_id, active=True)


def soft_delete_service(membership: Membership, public_id: UUID | str) -> Service:
    """Regla 39: borrado lógico. El historial lo conserva y el nombre queda libre."""
    ensure_permission(membership, "servicios.eliminar")
    with transaction.atomic():
        service = _live_service_for_update(public_id)
        before = _service_snapshot(service)
        service.soft_delete(by=membership.user)
        _audit(membership, "servicio.eliminar", service, before=before, after=_service_snapshot(service))
    return service


# ── Categorías ───────────────────────────────────────────────────────────────


def create_category(membership: Membership, *, name: str) -> ServiceCategory:
    ensure_permission(membership, "servicios.crear")
    with transaction.atomic():
        category = ServiceCategory(barbershop_id=membership.barbershop_id, name=name.strip())
        _save_validated(category, DUPLICATE_CATEGORY)
        _audit(membership, "categoria_servicio.crear", category, before=None, after=_category_snapshot(category))
    return category


def update_category(membership: Membership, public_id: UUID | str, *, name: str) -> ServiceCategory:
    ensure_permission(membership, "servicios.editar")
    with transaction.atomic():
        category = _live_category_for_update(public_id)
        before = _category_snapshot(category)
        category.name = name.strip()
        _save_validated(category, DUPLICATE_CATEGORY)
        after = _category_snapshot(category)
        if after != before:
            _audit(membership, "categoria_servicio.editar", category, before=before, after=after)
    return category


def soft_delete_category(membership: Membership, public_id: UUID | str) -> ServiceCategory:
    """Borrado lógico. Los servicios vivos de la categoría quedan sin categoría."""
    ensure_permission(membership, "servicios.eliminar")
    with transaction.atomic():
        category = _live_category_for_update(public_id)
        before = _category_snapshot(category)
        live_services = Service.objects.select_for_update().filter(category=category, deleted_at__isnull=True)
        detached = [str(service_id) for service_id in live_services.values_list("public_id", flat=True)]
        live_services.update(category=None, updated_at=timezone.now())
        category.soft_delete(by=membership.user)
        after = {**_category_snapshot(category), "detached_services": detached}
        _audit(membership, "categoria_servicio.eliminar", category, before=before, after=after)
    return category
