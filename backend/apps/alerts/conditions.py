"""Qué alertas deberían estar abiertas hoy en la barbería activa.

Cada condición vigente es una clave (tipo, id de la referencia, id de la sede) con su mensaje.
`services.generate_alerts` compara estas claves con las alertas abiertas: crea las que faltan y
resuelve las que ya no corresponden.

Fase S4b de docs/sedes.md: las de inventario son por existencia de cada sede. El mínimo es del
producto y se compara con la existencia de cada sede; por vencer solo donde hay unidades.
"""

from datetime import date, timedelta

from django.db.models import F, Q, QuerySet

from apps.alerts.models import AlertType
from apps.core.formatting import format_cop, short_date
from apps.inventory.models import StockLevel
from apps.receivables.models import Receivable, ReceivableStatus

# Un producto "por vencer" vence dentro de estos días (los ya vencidos también cuentan).
EXPIRING_WINDOW_DAYS = 30

AlertKey = tuple[str, int, int]

OUT_OF_STOCK = Q(quantity__lte=0)
# Un agotado ya tiene su alerta: stock bajo es solo para el que aún tiene unidades.
LOW_STOCK = Q(product__minimum_stock__isnull=False, quantity__gt=0, quantity__lte=F("product__minimum_stock"))


def alertable_levels() -> QuerySet[StockLevel]:
    """Existencias de productos vivos y activos en sedes activas."""
    return StockLevel.objects.filter(
        product__deleted_at__isnull=True, product__is_active=True, branch__is_active=True
    ).select_related("product", "branch")


def _key(alert_type: str, level: StockLevel) -> AlertKey:
    return (alert_type, level.product_id, level.branch_id)


def _stock_conditions() -> dict[AlertKey, str]:
    levels = alertable_levels()
    out_of_stock = {
        _key(AlertType.OUT_OF_STOCK, level): f"{level.product.name} está agotado en {level.branch.name}."
        for level in levels.filter(OUT_OF_STOCK)
    }
    low_stock = {
        _key(AlertType.LOW_STOCK, level): (
            f"{level.product.name} tiene stock bajo en {level.branch.name}: "
            f"quedan {level.quantity} (mínimo {level.product.minimum_stock})."
        )
        for level in levels.filter(LOW_STOCK)
    }
    return out_of_stock | low_stock


def _expiry_conditions(today: date) -> dict[AlertKey, str]:
    limit = today + timedelta(days=EXPIRING_WINDOW_DAYS)
    expiring = alertable_levels().filter(
        quantity__gt=0, product__expiration_date__isnull=False, product__expiration_date__lte=limit
    )
    messages = {}
    for level in expiring:
        product = level.product
        verb = "venció" if product.expiration_date < today else "vence"
        when = f"{verb} el {short_date(product.expiration_date)}"
        messages[_key(AlertType.EXPIRING, level)] = (
            f"{product.name} {when}; hay {level.quantity} en {level.branch.name}."
        )
    return messages


def _receivable_conditions() -> dict[AlertKey, str]:
    overdue = Receivable.objects.filter(status=ReceivableStatus.OVERDUE, balance__gt=0).select_related("client")
    return {
        (AlertType.OVERDUE_RECEIVABLE, r.pk, r.origin_branch_id): (
            f"El fiado de {r.client} está vencido; saldo {format_cop(r.balance)}."
        )
        for r in overdue
    }


def current_conditions(today: date) -> dict[AlertKey, str]:
    return _stock_conditions() | _expiry_conditions(today) | _receivable_conditions()
