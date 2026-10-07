"""Personal de cada barbería: barberos y su historial de comisiones.

Portado de MAGNUS v1 (`models/barber.py`) según `docs/migracion-magnus.md`.
La comisión deja de ser un campo del barbero (que al cambiar reescribía las
comisiones pasadas, defecto 1) y pasa a reglas solo-agregar con vigencia.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import SoftDeleteModel, TenantManager, TenantQuerySet, TenantScopedModel


class Barber(TenantScopedModel, SoftDeleteModel):
    display_name = models.CharField("nombre", max_length=120)
    alias = models.CharField(max_length=80, blank=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)
    branch = models.ForeignKey(
        "tenancy.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="barbers"
    )
    # Regla 41: una membresía se vincula a lo sumo a un barbero, aunque ese barbero esté borrado.
    membership = models.OneToOneField(
        "tenancy.Membership", null=True, blank=True, on_delete=models.PROTECT, related_name="barber"
    )
    is_active = models.BooleanField("activo", default=True)
    notes = models.TextField("notas", blank=True)

    def __str__(self) -> str:
        return self.display_name


class CommissionType(models.TextChoices):
    PERCENTAGE = "percentage", "Porcentaje"
    FIXED = "fixed", "Monto fijo"


class AppendOnlyQuerySet(TenantQuerySet):
    def update(self, **kwargs):
        raise PermissionError("Tabla solo-agregar: no se modifica.")

    def delete(self):
        raise PermissionError("Tabla solo-agregar: no se borra.")


class CommissionRule(TenantScopedModel):
    """Comisión de un barbero vigente desde `valid_from`. Solo-agregar.

    Decisión 3: el porcentaje aplica al precio neto de cada línea de servicio; el
    monto fijo, por unidad de servicio. `service` nulo es la regla general.
    Cambiar la comisión es crear una regla nueva; sales copia el valor al cerrar.
    """

    barber = models.ForeignKey(Barber, on_delete=models.PROTECT, related_name="commission_rules")
    service = models.ForeignKey(
        "catalog.Service", null=True, blank=True, on_delete=models.PROTECT, related_name="commission_rules"
    )
    commission_type = models.CharField("tipo", max_length=12, choices=CommissionType.choices)
    value = models.DecimalField("valor", max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    valid_from = models.DateTimeField("vigente desde")

    objects = TenantManager.from_queryset(AppendOnlyQuerySet)()

    class Meta:
        # Redefinir `objects` lo deja después de `unscoped` (heredado): sin esto, el
        # manager por defecto sería el que no filtra por barbería.
        default_manager_name = "objects"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(commission_type__in=CommissionType.values), name="ck_commissionrule_type_valid"
            ),
            models.CheckConstraint(condition=models.Q(value__gte=0), name="ck_commissionrule_value_not_negative"),
            models.CheckConstraint(
                condition=models.Q(commission_type=CommissionType.FIXED) | models.Q(value__lte=100),
                name="ck_commissionrule_percentage_max_100",
                violation_error_message="Un porcentaje de comisión no puede ser mayor que 100.",
            ),
        ]
        indexes = [models.Index(fields=["barber", "service", "valid_from"])]

    def __str__(self) -> str:
        return f"{self.barber} · {self.get_commission_type_display()} {self.value}"

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None:
            raise PermissionError("Una regla de comisión no se modifica: crea una nueva.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Una regla de comisión no se borra.")
