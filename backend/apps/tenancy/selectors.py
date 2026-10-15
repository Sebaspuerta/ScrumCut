from collections.abc import Iterable
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.tenancy.models import Barbershop, Branch, Membership

INVALID_BRANCHES = "Alguna de las sedes no existe o está inactiva."


def active_memberships(user) -> list[Membership]:
    return list(
        Membership.objects.select_related("barbershop")
        .filter(user=user, is_active=True)
        .exclude(barbershop__status__in=[Barbershop.Status.SUSPENDED, Barbershop.Status.CLOSED])
    )


def membership_for(user, barbershop_id: int) -> Membership | None:
    return next((m for m in active_memberships(user) if m.barbershop_id == barbershop_id), None)


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
