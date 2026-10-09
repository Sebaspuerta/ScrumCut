"""Alertas automáticas de cada barbería: inventario y fiados vencidos.

Portado de MAGNUS v1 (`models/alerts.py`) según `docs/migracion-magnus.md`. La
referencia deja de ser `reference_type` + `reference_id` sueltos: son FK con
PROTECT al producto o al fiado. Solo la tarea `generar_alertas` las crea y las
resuelve: una alerta abierta (sin resolver, leída o no) se cierra sola cuando su
condición desaparece.
"""

from django.db import models

from apps.core.models import TenantScopedModel


class AlertType(models.TextChoices):
    OUT_OF_STOCK = "agotado", "Agotado"
    LOW_STOCK = "stock_bajo", "Stock bajo"
    EXPIRING = "por_vencer", "Por vencer"
    OVERDUE_RECEIVABLE = "fiado_vencido", "Fiado vencido"


PRODUCT_ALERT_TYPES = (AlertType.OUT_OF_STOCK, AlertType.LOW_STOCK, AlertType.EXPIRING)


class Alert(TenantScopedModel):
    alert_type = models.CharField("tipo", max_length=16, choices=AlertType.choices)
    product = models.ForeignKey(
        "inventory.Product", null=True, blank=True, on_delete=models.PROTECT, related_name="alerts"
    )
    receivable = models.ForeignKey(
        "receivables.Receivable", null=True, blank=True, on_delete=models.PROTECT, related_name="alerts"
    )
    message = models.TextField("mensaje")
    read_at = models.DateTimeField("leída", null=True, blank=True)
    read_by = models.ForeignKey("tenancy.Membership", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    resolved_at = models.DateTimeField("resuelta", null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(alert_type__in=AlertType.values), name="ck_alert_type_valid"),
            # Las de inventario apuntan a un producto; la de fiado, a un fiado. Nunca a ambos.
            models.CheckConstraint(
                condition=models.Q(alert_type__in=PRODUCT_ALERT_TYPES, product__isnull=False, receivable__isnull=True)
                | models.Q(alert_type=AlertType.OVERDUE_RECEIVABLE, receivable__isnull=False, product__isnull=True),
                name="ck_alert_reference_matches_type",
            ),
            models.CheckConstraint(
                condition=models.Q(read_at__isnull=True, read_by__isnull=True)
                | models.Q(read_at__isnull=False, read_by__isnull=False),
                name="ck_alert_read_fields_together",
            ),
            # Regla 48: una sola alerta abierta por tipo y referencia.
            models.UniqueConstraint(
                fields=["alert_type", "product"],
                condition=models.Q(resolved_at__isnull=True, product__isnull=False),
                name="uq_alert_open_per_product",
            ),
            models.UniqueConstraint(
                fields=["alert_type", "receivable"],
                condition=models.Q(resolved_at__isnull=True, receivable__isnull=False),
                name="uq_alert_open_per_receivable",
            ),
        ]
        indexes = [models.Index(fields=["barbershop", "read_at", "created_at"])]

    def __str__(self) -> str:
        return f"{self.get_alert_type_display()}: {self.message}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
