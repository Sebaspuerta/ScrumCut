"""Lecturas de personal. Los managers ya filtran por la barbería activa."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from django.db.models import QuerySet
from django.db.models.functions import Lower

from apps.catalog.models import Service
from apps.staff.models import Barber, CommissionRule, CommissionType
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_member, ensure_permission


def resolve_commission(barber: Barber, service: Service | None, at: datetime) -> tuple[str, Decimal]:
    """Comisión vigente en `at`: la regla del servicio si existe, si no la general.

    Sin reglas devuelve (porcentaje, 0). sales la llama al cerrar la comanda y
    copia el resultado en la línea; no exige permiso porque no expone datos.
    """
    rules = CommissionRule.objects.filter(barber=barber, valid_from__lte=at).order_by("-valid_from", "-pk")
    rule = None
    if service is not None:
        rule = rules.filter(service=service).first()
    if rule is None:
        rule = rules.filter(service__isnull=True).first()
    if rule is None:
        return CommissionType.PERCENTAGE, Decimal("0")
    return rule.commission_type, rule.value


def list_barbers(membership: Membership, *, active_only: bool = True) -> QuerySet[Barber]:
    ensure_permission(membership, "barberos.ver")
    barbers = Barber.objects.filter(deleted_at__isnull=True).select_related("branch", "membership__user")
    if active_only:
        barbers = barbers.filter(is_active=True)
    return barbers.order_by(Lower("display_name"))


def get_barber(membership: Membership, public_id: UUID | str) -> Barber:
    """Incluye desactivados; nunca borrados. Lanza `Barber.DoesNotExist`."""
    ensure_permission(membership, "barberos.ver")
    return Barber.objects.select_related("branch", "membership__user").get(public_id=public_id, deleted_at__isnull=True)


def list_active_barbers_basic(membership: Membership) -> list[dict]:
    """Regla 45: solo identificador y nombre, para los formularios de comandas.

    Basta una membresía activa de la barbería: no expone teléfono, notas ni comisiones.
    """
    ensure_member(membership)
    barbers = Barber.objects.filter(deleted_at__isnull=True, is_active=True).order_by(Lower("display_name"))
    return list(barbers.values("public_id", "display_name"))
