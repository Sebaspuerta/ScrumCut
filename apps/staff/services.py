"""Escrituras de personal.

Reglas portadas de MAGNUS v1 (`services/barber_service.py`), numeradas como en
`docs/migracion-magnus.md`: 41 (una membresía, un barbero) y 42 (el barbero del
dueño no se borra). La comisión sigue la decisión 3 y corrige el defecto 1: se
cambia creando una regla nueva, nunca editando la vigente.

Igual que en catalog: un objeto inexistente, de otra barbería o borrado lanza
`DoesNotExist`; los datos inválidos, `ValidationError`.
"""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import record
from apps.catalog.models import Service
from apps.core.tenant_context import get_current_barbershop_id
from apps.staff.models import Barber, CommissionRule
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission
from apps.tenancy.roles import Role

_CENTS = Decimal("0.01")
_TEXT_FIELDS = ("display_name", "alias", "phone", "notes")

MEMBERSHIP_TAKEN = "Esa membresía ya está vinculada a otro barbero."
# El dueño o el administrador que también corta es lo normal; cajero y consultor no atienden.
LINKABLE_ROLES = frozenset({Role.BARBER, Role.OWNER, Role.ADMIN})


class BarberData(TypedDict, total=False):
    display_name: str
    alias: str
    phone: str
    notes: str
    branch: UUID | str | None
    membership: UUID | str | None


def _audit(actor: Membership, action: str, obj, *, before: dict | None, after: dict | None) -> None:
    record(
        action=action,
        entity=obj._meta.label,
        entity_id=str(obj.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        before=before,
        after=after,
    )


def _barber_snapshot(barber: Barber) -> dict:
    return {
        "display_name": barber.display_name,
        "alias": barber.alias,
        "phone": barber.phone,
        "notes": barber.notes,
        "branch": str(barber.branch.public_id) if barber.branch_id else None,
        "membership": str(barber.membership.public_id) if barber.membership_id else None,
        "is_active": barber.is_active,
        "deleted_at": barber.deleted_at.isoformat() if barber.deleted_at else None,
    }


def _rule_snapshot(rule: CommissionRule) -> dict:
    return {
        "barber": str(rule.barber.public_id),
        "service": str(rule.service.public_id) if rule.service_id else None,
        "commission_type": rule.commission_type,
        "value": str(Decimal(rule.value).quantize(_CENTS)),
        "valid_from": rule.valid_from.isoformat(),
    }


def _live_barber_for_update(public_id: UUID | str) -> Barber:
    return Barber.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)


def _resolve_branch(public_id: UUID | str | None) -> Branch | None:
    if public_id is None:
        return None
    try:
        return Branch.objects.get(public_id=public_id, is_active=True)
    except Branch.DoesNotExist as exc:
        raise ValidationError({"branch": "La sede no existe."}) from exc


def _resolve_service(public_id: UUID | str | None) -> Service | None:
    if public_id is None:
        return None
    try:
        return Service.objects.get(public_id=public_id, deleted_at__isnull=True)
    except Service.DoesNotExist as exc:
        raise ValidationError({"service": "El servicio no existe."}) from exc


def _resolve_membership(public_id: UUID | str | None, barber: Barber) -> Membership | None:
    """Regla 41: membresía activa, de esta barbería, con rol que corta y sin otro barbero."""
    if public_id is None:
        return None
    # Membership no es TenantScopedModel (se lee al iniciar sesión, antes de fijar la
    # barbería), así que aquí sí se filtra por la barbería activa de forma explícita.
    try:
        membership = Membership.objects.get(public_id=public_id, barbershop_id=get_current_barbershop_id())
    except Membership.DoesNotExist as exc:
        raise ValidationError({"membership": "La membresía no existe."}) from exc
    if membership.pk == barber.membership_id:
        return membership
    if not membership.is_active or membership.role not in LINKABLE_ROLES:
        raise ValidationError({"membership": "La membresía debe estar activa y ser de Barbero, Dueño o Administrador."})
    if Barber.objects.filter(membership=membership).exclude(pk=barber.pk).exists():
        raise ValidationError({"membership": MEMBERSHIP_TAKEN})
    return membership


def _apply(barber: Barber, data: BarberData) -> None:
    unknown = set(data) - set(BarberData.__annotations__)
    if unknown:
        raise TypeError(f"Campos desconocidos: {sorted(unknown)}")
    for field in _TEXT_FIELDS:
        if field in data:
            setattr(barber, field, (data[field] or "").strip())
    if "branch" in data:
        barber.branch = _resolve_branch(data["branch"])
    if "membership" in data:
        barber.membership = _resolve_membership(data["membership"], barber)


def _save_validated(barber: Barber) -> None:
    barber.full_clean()
    try:
        with transaction.atomic():
            barber.save()
    except IntegrityError as exc:
        # Dos solicitudes simultáneas pueden vincular la misma membresía: decide la base.
        raise ValidationError({"membership": MEMBERSHIP_TAKEN}) from exc


def _create_rule(
    barber: Barber, commission_type: str, value, *, service: Service | None, valid_from: datetime
) -> CommissionRule:
    rule = CommissionRule(
        barbershop_id=barber.barbershop_id,
        barber=barber,
        service=service,
        commission_type=commission_type,
        value=value,
        valid_from=valid_from,
    )
    rule.full_clean()
    rule.save()
    return rule


# ── Barberos ─────────────────────────────────────────────────────────────────


def create_barber(membership_actor: Membership, data: BarberData, commission_type: str, commission_value) -> Barber:
    """Crea el barbero y su regla de comisión general, vigente desde ahora."""
    ensure_permission(membership_actor, "barberos.crear")
    with transaction.atomic():
        barber = Barber(barbershop_id=membership_actor.barbershop_id)
        _apply(barber, data)
        _save_validated(barber)
        rule = _create_rule(barber, commission_type, commission_value, service=None, valid_from=timezone.now())
        after = {**_barber_snapshot(barber), "commission": _rule_snapshot(rule)}
        _audit(membership_actor, "barbero.crear", barber, before=None, after=after)
    return barber


def update_barber(membership_actor: Membership, public_id: UUID | str, data: BarberData) -> Barber:
    """Solo cambia las claves presentes en `data`. `membership=None` desvincula."""
    ensure_permission(membership_actor, "barberos.editar")
    with transaction.atomic():
        barber = _live_barber_for_update(public_id)
        before = _barber_snapshot(barber)
        _apply(barber, data)
        _save_validated(barber)
        after = _barber_snapshot(barber)
        if after != before:
            _audit(membership_actor, "barbero.editar", barber, before=before, after=after)
    return barber


def _set_barber_active(membership_actor: Membership, public_id: UUID | str, *, active: bool) -> Barber:
    ensure_permission(membership_actor, "barberos.editar")
    with transaction.atomic():
        barber = _live_barber_for_update(public_id)
        if barber.is_active == active:
            return barber
        before = _barber_snapshot(barber)
        barber.is_active = active
        barber.save(update_fields=["is_active", "updated_at"])
        action = "barbero.activar" if active else "barbero.desactivar"
        _audit(membership_actor, action, barber, before=before, after=_barber_snapshot(barber))
    return barber


def deactivate_barber(membership_actor: Membership, public_id: UUID | str) -> Barber:
    return _set_barber_active(membership_actor, public_id, active=False)


def activate_barber(membership_actor: Membership, public_id: UUID | str) -> Barber:
    return _set_barber_active(membership_actor, public_id, active=True)


def soft_delete_barber(membership_actor: Membership, public_id: UUID | str) -> Barber:
    """Borrado lógico; las comandas y comisiones ya registradas quedan intactas.

    Desvincula la membresía para que la persona pueda volver a vincularse a otro
    barbero; la auditoría guarda cuál era.
    """
    ensure_permission(membership_actor, "barberos.eliminar")
    with transaction.atomic():
        barber = _live_barber_for_update(public_id)
        if barber.membership_id and barber.membership.role == Role.OWNER:
            raise ValidationError("No se puede eliminar al barbero vinculado al dueño de la barbería.")
        before = _barber_snapshot(barber)
        barber.membership = None
        barber.save(update_fields=["membership", "updated_at"])
        barber.soft_delete(by=membership_actor.user)
        after = {**_barber_snapshot(barber), "unlinked_membership": before["membership"]}
        _audit(membership_actor, "barbero.eliminar", barber, before=before, after=after)
    return barber


# ── Comisiones ───────────────────────────────────────────────────────────────


def set_commission(
    membership_actor: Membership,
    barber: UUID | str,
    commission_type: str,
    value,
    service: UUID | str | None = None,
    valid_from: datetime | None = None,
) -> CommissionRule:
    """Crea una regla nueva vigente desde `valid_from` (por defecto, ahora).

    No se aceptan fechas pasadas: una regla retroactiva cambiaría lo que
    `resolve_commission` devuelve para fechas ya causadas.
    """
    ensure_permission(membership_actor, "barberos.editar")
    now = timezone.now()
    if valid_from is None:
        valid_from = now
    elif timezone.is_naive(valid_from):
        raise ValidationError({"valid_from": "La fecha de vigencia debe incluir zona horaria."})
    elif valid_from < now:
        raise ValidationError({"valid_from": "Una comisión no puede empezar en el pasado."})
    with transaction.atomic():
        target = _live_barber_for_update(barber)
        rule = _create_rule(target, commission_type, value, service=_resolve_service(service), valid_from=valid_from)
        _audit(membership_actor, "comision.crear", rule, before=None, after=_rule_snapshot(rule))
    return rule
