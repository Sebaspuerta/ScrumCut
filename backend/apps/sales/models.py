"""Comandas (ventas) de cada barbería.

Portado de MAGNUS v1 (`models/order.py`, `payment.py`) según `docs/migracion-magnus.md`.
Al cerrar, cada línea guarda nombre, precio, costo y comisión (regla 10 de
`AGENTS.md`, defecto 1): los reportes leen esas copias, nunca el catálogo actual.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.cash.choices import PaymentMethod
from apps.core.models import AppendOnlyModel, TenantScopedModel

_MONEY = {"max_digits": 14, "decimal_places": 2}
_ZERO = Decimal("0")


class OrderStatus(models.TextChoices):
    OPEN = "abierta", "Abierta"
    ON_HOLD = "en_espera", "En espera"
    CLOSED = "cerrada", "Cerrada"
    CANCELLED = "anulada", "Anulada"


EDITABLE_STATUSES = (OrderStatus.OPEN, OrderStatus.ON_HOLD)


class PaymentStatus(models.TextChoices):
    PENDING = "pendiente", "Pendiente"
    PAID = "pagado", "Pagado"
    CREDIT = "fiado", "Fiado"


class Order(TenantScopedModel):
    number = models.PositiveIntegerField("número", editable=False)
    branch = models.ForeignKey("tenancy.Branch", on_delete=models.PROTECT, related_name="orders")
    client = models.ForeignKey("clients.Client", null=True, blank=True, on_delete=models.PROTECT, related_name="orders")
    barber = models.ForeignKey("staff.Barber", null=True, blank=True, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField("estado", max_length=10, choices=OrderStatus.choices, default=OrderStatus.OPEN)
    payment_status = models.CharField(
        "estado de pago", max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    subtotal = models.DecimalField("subtotal", default=_ZERO, **_MONEY)
    discount = models.DecimalField("descuento", default=_ZERO, validators=[MinValueValidator(_ZERO)], **_MONEY)
    discount_reason = models.TextField("motivo del descuento", blank=True)
    total = models.DecimalField("total", default=_ZERO, **_MONEY)
    amount_paid = models.DecimalField("pagado", default=_ZERO, **_MONEY)
    commission_total = models.DecimalField("comisiones", default=_ZERO, **_MONEY)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    closed_at = models.DateTimeField("cerrada", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    cancelled_at = models.DateTimeField("anulada", null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    cancel_reason = models.TextField("motivo de anulación", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["barbershop", "number"],
                name="uq_order_number_per_barbershop",
                violation_error_message="Ese número de comanda ya existe.",
            ),
            models.CheckConstraint(condition=models.Q(status__in=OrderStatus.values), name="ck_order_status_valid"),
            models.CheckConstraint(
                condition=models.Q(payment_status__in=PaymentStatus.values), name="ck_order_payment_status_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(discount__gte=0, discount__lte=models.F("subtotal")),
                name="ck_order_discount_within_subtotal",
                violation_error_message="El descuento no puede superar el subtotal.",
            ),
            models.CheckConstraint(
                condition=models.Q(discount=0) | ~models.Q(discount_reason=""),
                name="ck_order_discount_has_reason",
                violation_error_message="Un descuento necesita motivo.",
            ),
            models.CheckConstraint(
                condition=models.Q(total=models.F("subtotal") - models.F("discount")), name="ck_order_total_adds_up"
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0, amount_paid__lte=models.F("total")),
                name="ck_order_paid_within_total",
                violation_error_message="Lo pagado no puede superar el total.",
            ),
            models.CheckConstraint(
                condition=~models.Q(status=OrderStatus.CLOSED) | models.Q(closed_at__isnull=False),
                name="ck_order_closed_has_date",
            ),
            models.CheckConstraint(
                condition=~models.Q(status=OrderStatus.CANCELLED)
                | (models.Q(cancelled_at__isnull=False) & ~models.Q(cancel_reason="")),
                name="ck_order_cancelled_has_reason",
            ),
        ]
        indexes = [models.Index(fields=["barbershop", "status", "closed_at"])]

    def __str__(self) -> str:
        return f"Comanda #{self.number}"

    @property
    def balance(self) -> Decimal:
        return self.total - self.amount_paid


class ItemType(models.TextChoices):
    SERVICE = "servicio", "Servicio"
    PRODUCT = "producto", "Producto"


class OrderItem(TenantScopedModel):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    item_type = models.CharField("tipo", max_length=10, choices=ItemType.choices)
    service = models.ForeignKey("catalog.Service", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    product = models.ForeignKey("inventory.Product", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    barber = models.ForeignKey("staff.Barber", null=True, blank=True, on_delete=models.PROTECT, related_name="items")
    quantity = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])
    # El precio sale del catálogo al agregar la línea; lo demás se copia al cerrar.
    name = models.CharField("nombre", max_length=120)
    unit_price = models.DecimalField("precio unitario", validators=[MinValueValidator(_ZERO)], **_MONEY)
    line_total = models.DecimalField("total de la línea", **_MONEY)
    line_discount = models.DecimalField("descuento repartido", default=_ZERO, **_MONEY)
    unit_cost = models.DecimalField("costo unitario", default=_ZERO, **_MONEY)
    consumables_cost = models.DecimalField("costo de insumos", default=_ZERO, **_MONEY)
    commission_type = models.CharField("tipo de comisión", max_length=12, blank=True)
    commission_rate = models.DecimalField("valor de comisión", null=True, blank=True, **_MONEY)
    commission_amount = models.DecimalField("comisión", default=_ZERO, **_MONEY)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(item_type=ItemType.SERVICE, service__isnull=False, product__isnull=True)
                | models.Q(item_type=ItemType.PRODUCT, product__isnull=False, service__isnull=True),
                name="ck_orderitem_one_reference_by_type",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="ck_orderitem_quantity_positive"),
            models.CheckConstraint(
                condition=models.Q(line_total=models.F("unit_price") * models.F("quantity")),
                name="ck_orderitem_line_total_adds_up",
            ),
            models.CheckConstraint(
                condition=models.Q(line_discount__gte=0, line_discount__lte=models.F("line_total")),
                name="ck_orderitem_discount_within_line",
            ),
            models.CheckConstraint(
                condition=models.Q(commission_amount__gte=0), name="ck_orderitem_commission_not_negative"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} × {self.quantity}"


class Payment(AppendOnlyModel):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    cash_movement = models.OneToOneField("cash.CashMovement", on_delete=models.PROTECT, related_name="sale_payment")
    method = models.CharField("método", max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField("monto", validators=[MinValueValidator(Decimal("0.01"))], **_MONEY)
    reference = models.CharField("referencia", max_length=80, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_payment_amount_positive"),
            models.CheckConstraint(condition=models.Q(method__in=PaymentMethod.values), name="ck_payment_method_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.order} · {self.get_method_display()} {self.amount}"
