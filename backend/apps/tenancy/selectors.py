from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.tenancy.models import Barbershop, Branch, Membership
from apps.tenancy.roles import Role

INVALID_BRANCHES = "Alguna de las sedes no existe o está inactiva."


def active_memberships(user) -> list[Membership]:
    return list(
        Membership.objects.select_related("barbershop")
        .filter(user=user, is_active=True)
        .exclude(barbershop__status__in=[Barbershop.Status.SUSPENDED, Barbershop.Status.CLOSED])
    )


def membership_for(user, barbershop_id: int) -> Membership | None:
    return next((m for m in active_memberships(user) if m.barbershop_id == barbershop_id), None)


class Access(StrEnum):
    """Por qué la persona entra o no a una barbería (pantallas de pérdida de acceso de la app)."""

    ACTIVE = "active"
    NO_BARBERSHOP = "no_barbershop"
    MEMBERSHIP_INACTIVE = "membership_inactive"
    BARBERSHOP_SUSPENDED = "barbershop_suspended"
    BARBERSHOP_CLOSED = "barbershop_closed"
    SEVERAL_BARBERSHOPS = "several_barbershops"


@dataclass(frozen=True)
class AccessState:
    status: Access
    barbershop: str | None = None  # siempre una barbería de la propia persona
    # El contacto de ScrumTech: para el dueño de una barbería suspendida o cerrada y para quien tiene varias.
    support_email: str | None = None


_BLOCKED_SHOPS = {
    Barbershop.Status.SUSPENDED: Access.BARBERSHOP_SUSPENDED,
    Barbershop.Status.CLOSED: Access.BARBERSHOP_CLOSED,
}


def _support_email() -> str | None:
    return settings.SUPPORT_EMAIL or None


def _blocked_shop(memberships: list[Membership]) -> AccessState | None:
    for shop_status, access in _BLOCKED_SHOPS.items():
        for membership in memberships:
            if membership.is_active and membership.barbershop.status == shop_status:
                owner = membership.role == Role.OWNER
                return AccessState(access, membership.barbershop.trade_name, _support_email() if owner else None)
    return None


def access_state(user, membership: Membership | None) -> AccessState:
    """El estado de acceso con solo las membresías de la persona: nunca dice nada de otra barbería."""
    if membership is not None:
        return AccessState(Access.ACTIVE, membership.barbershop.trade_name)
    memberships = list(Membership.objects.select_related("barbershop").filter(user=user).order_by("pk"))
    usable = [m for m in memberships if m.is_active and m.barbershop.is_operational]
    if len(usable) > 1:
        return AccessState(Access.SEVERAL_BARBERSHOPS, support_email=_support_email())
    if usable:
        return AccessState(Access.ACTIVE, usable[0].barbershop.trade_name)
    if blocked := _blocked_shop(memberships):
        return blocked
    revoked = next((m for m in memberships if not m.is_active), None)
    if revoked is not None:
        return AccessState(Access.MEMBERSHIP_INACTIVE, revoked.barbershop.trade_name)
    return AccessState(Access.NO_BARBERSHOP)


def active_branches(public_ids: Iterable[UUID | str]) -> list[Branch]:
    """Las sedes activas de la barbería activa con esos identificadores; si falta alguna, ValidationError."""
    wanted = {str(public_id) for public_id in public_ids}
    try:
        branches = list(Branch.objects.filter(public_id__in=wanted, is_active=True))
    except ValidationError as exc:  # un identificador que no es UUID
        raise ValidationError({"branches": INVALID_BRANCHES}) from exc
    if len(branches) != len(wanted):
        raise ValidationError({"branches": INVALID_BRANCHES})
    return branches


def plan_usage(barbershop: Barbershop) -> dict:
    """Sedes activas frente al límite del plan (decisión 8 de docs/sedes.md)."""
    return {"active": Branch.objects.filter(is_active=True).count(), "limit": barbershop.max_branches}


def active_member_count(barbershop: Barbershop) -> int:
    # Membership no lleva RLS (docs/sedes.md): se filtra por la barbería aquí, nunca en una vista.
    return Membership.objects.filter(barbershop=barbershop, is_active=True).count()
