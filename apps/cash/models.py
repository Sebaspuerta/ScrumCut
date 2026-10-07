"""Caja de cada sede: sesiones de apertura y cierre, y un solo libro de movimientos.

Portado de MAGNUS v1 (`models/cash_register.py`, `cash_movement.py`) según
`docs/migracion-magnus.md`. Decisión 2: una caja abierta por sede, garantizada por
la base (defecto 17). Todo dinero, de cualquier método, es un `CashMovement`
(defecto 21); el arqueo se calcula solo desde ese libro (defectos 18 y 20).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.cash.choices import PaymentMethod
from apps.core.models import AppendOnlyModel, TenantScopedModel

_MONEY = {"max_digits": 14, "decimal_places": 2}


class CashSession(TenantScopedModel):
    branch = models.ForeignKey("tenancy.Branch", on_delete=models.PROTECT, related_name="cash_sessions")
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    opened_at = models.DateTimeField("abierta", default=timezone.now)
    opening_amount = models.DecimalField("base", validators=[MinValueValidator(Decimal("0"))], **_MONEY)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    closed_at = models.DateTimeField("cerrada", null=True, blank=True)
    counted_amount = models.DecimalField(
        "efectivo contado", null=True, blank=True, validators=[MinValueValidator(Decimal("0"))], **_MONEY
    )
    expected_amount = models.DecimalField("efectivo esperado", null=True, blank=True, **_MONEY)
    difference = models.DecimalField("diferencia", null=True, blank=True, **_MONEY)  # contado − esperado
    notes = models.TextField("notas", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["barbershop", "branch"],
                condition=models.Q(closed_at__isnull=True),
                name="uq_cashsession_one_open_per_branch",
                violation_error_message="Ya hay una caja abierta en esta sede.",
            ),
            models.CheckConstraint(
                condition=models.Q(opening_amount__gte=0), name="ck_cashsession_opening_not_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(counted_amount__isnull=True) | models.Q(counted_amount__gte=0),
                name="ck_cashsession_counted_not_negative",
            ),
            # Abierta: sin datos de cierre. Cerrada: con todos.
            models.CheckConstraint(
                condition=models.Q(
                    closed_at__isnull=True,
                    closed_by__isnull=True,
                    counted_amount__isnull=True,
                    expected_amount__isnull=True,
                    difference__isnull=True,
                )
                | models.Q(
                    closed_at__isnull=False,
                    closed_by__isnull=False,
                    counted_amount__isnull=False,
                    expected_amount__isnull=False,
                    difference__isnull=False,
                ),
                name="ck_cashsession_close_fields_together",
            ),
        ]

    def __str__(self) -> str:
        return f"Caja {self.branch} · {self.opened_at:%Y-%m-%d %H:%M}"

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


class MovementKind(models.TextChoices):
    SALE = "venta", "Venta"
    RECEIVABLE_PAYMENT = "abono_fiado", "Abono de fiado"
    MANUAL_INCOME = "ingreso_manual", "Ingreso manual"
    EXPENSE = "gasto", "Gasto"
    WITHDRAWAL = "retiro", "Retiro"
    ADJUSTMENT = "ajuste", "Ajuste"


class Direction(models.TextChoices):
    IN = "in", "Entrada"
    OUT = "out", "Salida"


INCOME_KINDS = (MovementKind.SALE, MovementKind.RECEIVABLE_PAYMENT, MovementKind.MANUAL_INCOME)
OUTFLOW_KINDS = (MovementKind.EXPENSE, MovementKind.WITHDRAWAL)


class CashMovement(AppendOnlyModel):
    session = models.ForeignKey(CashSession, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField("tipo", max_length=16, choices=MovementKind.choices)
    direction = models.CharField("sentido", max_length=3, choices=Direction.choices)
    amount = models.DecimalField("monto", validators=[MinValueValidator(Decimal("0.01"))], **_MONEY)
    payment_method = models.CharField("método de pago", max_length=20, choices=PaymentMethod.choices)
    description = models.TextField("descripción")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_cashmovement_amount_positive"),
            models.CheckConstraint(condition=~models.Q(description=""), name="ck_cashmovement_description_present"),
            models.CheckConstraint(condition=models.Q(kind__in=MovementKind.values), name="ck_cashmovement_kind_valid"),
            models.CheckConstraint(
                condition=models.Q(payment_method__in=PaymentMethod.values), name="ck_cashmovement_method_valid"
            ),
            # Ventas, abonos e ingresos entran; gastos y retiros salen; un ajuste puede ir en ambos sentidos.
            models.CheckConstraint(
                condition=models.Q(kind__in=INCOME_KINDS, direction=Direction.IN)
                | models.Q(kind__in=OUTFLOW_KINDS, direction=Direction.OUT)
                | models.Q(kind=MovementKind.ADJUSTMENT, direction__in=Direction.values),
                name="ck_cashmovement_kind_matches_direction",
            ),
        ]
        indexes = [models.Index(fields=["session", "payment_method"])]

    def __str__(self) -> str:
        sign = "+" if self.direction == Direction.IN else "−"
        return f"{self.get_kind_display()} {sign}{self.amount} ({self.get_payment_method_display()})"
