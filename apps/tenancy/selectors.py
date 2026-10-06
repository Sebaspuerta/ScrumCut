from apps.tenancy.models import Barbershop, Membership


def active_memberships(user) -> list[Membership]:
    return list(
        Membership.objects.select_related("barbershop")
        .filter(user=user, is_active=True)
        .exclude(barbershop__status__in=[Barbershop.Status.SUSPENDED, Barbershop.Status.CLOSED])
    )


def membership_for(user, barbershop_id: int) -> Membership | None:
    return next((m for m in active_memberships(user) if m.barbershop_id == barbershop_id), None)
