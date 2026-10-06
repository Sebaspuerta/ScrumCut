from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import TenantScopedModel, TimeStampedModel
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

    @property
    def is_operational(self) -> bool:
        return self.status in {self.Status.TRIAL, self.Status.ACTIVE}


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
