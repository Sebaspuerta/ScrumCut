"""Lecturas del catálogo. Los managers ya filtran por la barbería activa.

El permiso `servicios.ver` lo exige la vista con `require_permission`.
"""

from uuid import UUID

from django.db.models import QuerySet
from django.db.models.functions import Lower

from apps.catalog.models import Service, ServiceCategory


def list_services(*, active_only: bool = True) -> QuerySet[Service]:
    services = Service.objects.filter(deleted_at__isnull=True).select_related("category")
    if active_only:
        services = services.filter(is_active=True)
    return services.order_by(Lower("name"))


def get_service(public_id: UUID | str) -> Service:
    """Incluye desactivados; nunca borrados. Lanza `Service.DoesNotExist`."""
    return Service.objects.select_related("category").get(public_id=public_id, deleted_at__isnull=True)


def list_categories() -> QuerySet[ServiceCategory]:
    return ServiceCategory.objects.filter(deleted_at__isnull=True).order_by(Lower("name"))
