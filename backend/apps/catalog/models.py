"""Catálogo de servicios de cada barbería.

Portado de MAGNUS v1 (`models/service.py`) según `docs/migracion-magnus.md`:
la categoría deja de ser texto libre y el nombre es único también entre los
servicios desactivados (defecto 32); solo un borrado lógico libera el nombre.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import SoftDeleteModel, TenantScopedModel


class ServiceCategory(TenantScopedModel, SoftDeleteModel):
    name = models.CharField("nombre", max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                models.F("barbershop"),
                Lower("name"),
                condition=models.Q(deleted_at__isnull=True),
                name="uq_servicecategory_name_per_barbershop",
                violation_error_message="Ya existe una categoría con ese nombre.",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Service(TenantScopedModel, SoftDeleteModel):
    name = models.CharField("nombre", max_length=120)
    category = models.ForeignKey(
        ServiceCategory, null=True, blank=True, on_delete=models.PROTECT, related_name="services"
    )
    description = models.TextField("descripción", blank=True)
    price = models.DecimalField("precio", max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    duration_minutes = models.PositiveSmallIntegerField("duración en minutos", validators=[MinValueValidator(1)])
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                models.F("barbershop"),
                Lower("name"),
                condition=models.Q(deleted_at__isnull=True),
                name="uq_service_name_per_barbershop",
                violation_error_message="Ya existe un servicio con ese nombre.",
            ),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="ck_service_price_not_negative"),
            models.CheckConstraint(condition=models.Q(duration_minutes__gt=0), name="ck_service_duration_positive"),
            # Destino de la llave compuesta de ServiceBranchPrice (apps/core/tenant_keys.py).
            models.UniqueConstraint(fields=["barbershop", "id"], name="uq_service_barbershop_id"),
        ]

    def __str__(self) -> str:
        return self.name


class ServiceBranchPrice(TenantScopedModel):
    """Precio de un servicio en una sede (decisión 17 de docs/sedes.md).

    Sin fila, rige `Service.price`. Lo resuelve `apps.catalog.branch_prices.current_price`.
    """

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="branch_prices")
    branch = models.ForeignKey("tenancy.Branch", on_delete=models.PROTECT, related_name="service_prices")
    price = models.DecimalField(
        "precio en la sede", max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )

    class Meta:
        verbose_name = "precio de servicio en la sede"
        constraints = [
            models.UniqueConstraint(fields=["service", "branch"], name="uq_servicebranchprice_service_branch"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="ck_servicebranchprice_not_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.service} · {self.branch} · {self.price}"
