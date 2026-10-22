"""Lecturas de la auditoría. AuditLog no es de una sola barbería (hay eventos de plataforma), así que
toda lectura filtra por la barbería de la membresía aquí."""

from apps.audit.models import AuditLog
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission


def latest_event(membership: Membership) -> AuditLog | None:
    """El último cambio registrado en la barbería, con quién lo hizo."""
    ensure_permission(membership, "auditoria.ver")
    events = AuditLog.objects.filter(barbershop_id=membership.barbershop_id).select_related("actor")
    return events.order_by("-created_at", "-pk").first()
