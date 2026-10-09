"""Fiados (cuentas por cobrar) de cada barbería.

Portado de MAGNUS v1 (`models/accounts_receivable.py`) según `docs/migracion-magnus.md`.
El saldo nunca es negativo (defecto 24) y cada abono es un movimiento de caja.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.cash.choices import PaymentMethod
from apps.core.models import AppendOnlyModel, TenantScopedModel

_MONEY = {"max_digits": 14, "decimal_places": 2}


class ReceivableStatus(models.TextChoices):
    PENDING = "pendiente", "Pendiente"
    PAID = "pagado", "Pagado"
    OVERDUE = "vencido", "Vencido"
    CANCELLED = "anulado", "Anulado"


OPEN_STATUSES = (ReceivableStatus.PENDING, ReceivableStatus.OVERDUE)


class Receivable(TenantScopedModel):
    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="receivables")
    order = models.OneToOneField(
        "sales.Order", null=True, blank=True, on_delete=models.PROTECT, related_name="receivable"
    )
    total = models.DecimalField("total", validators=[MinValueValidator(Decimal("0.01"))], **_MONEY)
    balance = models.DecimalField("saldo", **_MONEY)
    status = models.CharField(
        "estado", max_length=10, choices=ReceivableStatus.choices, default=ReceivableStatus.PENDING
    )
    due_date = models.DateField("vence", null=True, blank=True)
    notes = models.TextField("notas", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gt=0), name="ck_receivable_total_positive"),
            models.CheckConstraint(
                condition=models.Q(balance__gte=0, balance__lte=models.F("total")),
                name="ck_receivable_balance_within_total",
                violation_error_message="El saldo no puede ser negativo ni mayor que el total.",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ReceivableStatus.values), name="ck_receivable_status_valid"
            ),
            models.CheckConstraint(
                condition=~models.Q(status=ReceivableStatus.PAID) | models.Q(balance=0),
                name="ck_receivable_paid_has_no_balance",
            ),
        ]
        indexes = [models.Index(fields=["barbershop", "status", "due_date"])]

    def __str__(self) -> str:
        return f"Fiado de {self.client} · saldo {self.balance}"


class ReceivablePayment(AppendOnlyModel):
    receivable = models.ForeignKey(Receivable, on_delete=models.PROTECT, related_name="payments")
    cash_movement = models.OneToOneField(
        "cash.CashMovement", on_delete=models.PROTECT, related_name="receivable_payment"
    )
    amount = models.DecimalField("monto", validators=[MinValueValidator(Decimal("0.01"))], **_MONEY)
    method = models.CharField("método", max_length=20, choices=PaymentMethod.choices)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_receivablepayment_amount_positive"),
            models.CheckConstraint(
                condition=models.Q(method__in=PaymentMethod.values), name="ck_receivablepayment_method_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"Abono {self.amount} a {self.receivable}"
