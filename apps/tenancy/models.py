from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.validators import ArrayMinLengthValidator
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.cash.choices import PaymentMethod, all_payment_methods
from apps.core.models import TenantScopedModel, TimeStampedModel
from apps.core.tenant_context import tenant_context
from apps.tenancy.roles import Role

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Usa un color hexadecimal, por ejemplo #B08D57.")


class Barbershop(TimeStampedModel):
    """El cliente de ScrumCut (tenant). Su identidad es dato, nunca código."""

    class Status(models.TextChoices):
        TRIAL = "trial", "Prueba"
        ACTIVE = "active", "Activa"
        SUSPENDED = "suspended", "Suspendida"
        CLOSED = "closed", "Cerrada"

    trade_name = models.CharField("nombre comercial", max_length=120)
    legal_name = models.CharField("razón social", max_length=160, blank=True)
    tax_id = models.CharField("NIT o documento", max_length=30, blank=True)
    tax_regime = models.CharField("régimen tributario", max_length=60, blank=True)
    slug = models.SlugField(max_length=60, unique=True)
    timezone = models.CharField(max_length=60, default="America/Bogota")
    currency = models.CharField(max_length=3, default="COP")
    logo = models.ImageField(upload_to="logos/", blank=True)
    accent_color = models.CharField(max_length=7, default="#B08D57", validators=[hex_color])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TRIAL)

    def __str__(self) -> str:
        return self.trade_name

    def save(self, *args, **kwargs) -> None:
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating:
            # RLS exige fijar la barbería para insertar su configuración.
            with tenant_context(self.pk):
                BarbershopSettings.objects.create(barbershop=self)

    @property
    def is_operational(self) -> bool:
        return self.status in {self.Status.TRIAL, self.Status.ACTIVE}


class BarbershopSettings(TenantScopedModel):
    """Configuración de negocio de una barbería. Se crea junto con ella."""

    barbershop = models.OneToOneField(Barbershop, on_delete=models.PROTECT, related_name="settings")
    # Decisión 5: umbrales del estado del cliente; por defecto, los de MAGNUS v1.
    vip_min_spent = models.DecimalField(
        "gasto mínimo VIP",
        max_digits=14,
        decimal_places=2,
        default=Decimal("200000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    vip_min_visits = models.PositiveIntegerField("visitas mínimas VIP", default=10)
    frequent_min_visits = models.PositiveIntegerField("visitas mínimas frecuente", default=3)
    inactive_after_days = models.PositiveIntegerField("días sin visita para inactivo", default=90)
    # Decisión 4: la barbería activa los métodos que usa; por defecto, todos.
    enabled_payment_methods = ArrayField(
        models.CharField(max_length=20, choices=PaymentMethod.choices),
        default=all_payment_methods,
        validators=[ArrayMinLengthValidator(1)],
        verbose_name="métodos de pago habilitados",
    )

    class Meta:
        verbose_name = "configuración de barbería"

    def __str__(self) -> str:
        return f"Configuración · {self.barbershop}"


class Branch(TenantScopedModel):
    """Sede. La v2 arranca con una por barbería."""

    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["barbershop", "name"], name="uq_branch_name_per_barbershop"),
        ]

    def __str__(self) -> str:
        return self.name


class Membership(TimeStampedModel):
    """Rol de una persona dentro de una barbería.

    No hereda de TenantScopedModel a propósito: se consulta al iniciar sesión,
    antes de que exista una barbería activa. Toda consulta pasa por selectors.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships")
    barbershop = models.ForeignKey(Barbershop, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=12, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "barbershop"], name="uq_membership_user_barbershop"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.barbershop} · {self.get_role_display()}"
