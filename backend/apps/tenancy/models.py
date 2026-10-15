from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.validators import ArrayMinLengthValidator
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models, transaction

from apps.cash.choices import PaymentMethod, all_payment_methods
from apps.core.models import TenantScopedModel, TimeStampedModel
from apps.core.tenant_context import tenant_context
from apps.tenancy.roles import Role

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Usa un color hexadecimal, por ejemplo #B08D57.")

# Decisión 12 de docs/sedes.md: toda barbería nace con esta sede.
MAIN_BRANCH_NAME = "Sede principal"


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
    # Límite del plan (decisión 8 de docs/sedes.md): cuenta solo las sedes activas.
    max_branches = models.PositiveSmallIntegerField("sedes del plan", default=1, validators=[MinValueValidator(1)])

    def __str__(self) -> str:
        return self.trade_name

    def save(self, *args, **kwargs) -> None:
        creating = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                # RLS exige fijar la barbería para insertar su configuración y su primera sede.
                with tenant_context(self.pk):
                    BarbershopSettings.objects.create(barbershop=self)
                    Branch.objects.create(barbershop=self, name=MAIN_BRANCH_NAME)

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
    # Consecutivo de comandas: sales lo lee y lo incrementa con select_for_update.
    next_order_number = models.PositiveIntegerField("siguiente número de comanda", default=1)
    # Tope de deuda viva por cliente. Nulo: sin límite.
    max_credit_per_client = models.DecimalField(
        "crédito máximo por cliente",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        verbose_name = "configuración de barbería"

    def __str__(self) -> str:
        return f"Configuración · {self.barbershop}"


class Branch(TenantScopedModel):
    """Sede. La v2 arranca con una por barbería."""

    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField("ciudad", max_length=80, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["barbershop", "name"], name="uq_branch_name_per_barbershop"),
            # Destino de las llaves compuestas (barbershop_id, branch_id): ver apps/core/tenant_keys.py.
            models.UniqueConstraint(fields=["barbershop", "id"], name="uq_branch_barbershop_id"),
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
    # Al iniciar sesión se vuelve a esta sede si sigue siendo válida (docs/sedes.md).
    last_branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="última sede"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "barbershop"], name="uq_membership_user_barbershop"),
            # Destino de la llave compuesta de MembershipBranch (apps/core/tenant_keys.py).
            models.UniqueConstraint(fields=["barbershop", "id"], name="uq_membership_barbershop_id"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.barbershop} · {self.get_role_display()}"


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Lunes"
    TUESDAY = 1, "Martes"
    WEDNESDAY = 2, "Miércoles"
    THURSDAY = 3, "Jueves"
    FRIDAY = 4, "Viernes"
    SATURDAY = 5, "Sábado"
    SUNDAY = 6, "Domingo"


class BranchHours(TenantScopedModel):
    """Horario de una sede por día de la semana. Un día cerrado no lleva horas."""

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="hours")
    weekday = models.PositiveSmallIntegerField(
        "día", choices=Weekday.choices, validators=[MaxValueValidator(Weekday.SUNDAY)]
    )
    opens_at = models.TimeField("abre", null=True, blank=True)
    closes_at = models.TimeField("cierra", null=True, blank=True)
    is_closed = models.BooleanField("cerrado", default=False)

    class Meta:
        verbose_name = "horario de sede"
        constraints = [
            models.UniqueConstraint(fields=["branch", "weekday"], name="uq_branchhours_branch_weekday"),
            models.CheckConstraint(condition=models.Q(weekday__lte=Weekday.SUNDAY), name="ck_branchhours_weekday"),
            models.CheckConstraint(
                condition=models.Q(is_closed=True)
                | models.Q(opens_at__isnull=False, closes_at__isnull=False, opens_at__lt=models.F("closes_at")),
                name="ck_branchhours_opens_before_closes",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.branch} · {self.get_weekday_display()}"


class MembershipBranch(TenantScopedModel):
    """Sedes a las que entra un Cajero (decisión 1 de docs/sedes.md). Los demás roles no la usan."""

    membership = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="branch_access")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="cashier_access")

    class Meta:
        verbose_name = "acceso de cajero a sede"
        constraints = [
            models.UniqueConstraint(fields=["membership", "branch"], name="uq_membershipbranch_membership_branch"),
        ]

    def __str__(self) -> str:
        return f"{self.membership} · {self.branch}"
