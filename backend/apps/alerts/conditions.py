"""Qué alertas deberían estar abiertas hoy en la barbería activa.

Cada condición vigente es una clave (tipo, id de la referencia) con su mensaje.
`services.generate_alerts` compara estas claves con las alertas abiertas: crea las
que faltan y resuelve las que ya no corresponden.
"""

from datetime import date, timedelta

from django.db.models import F, QuerySet

from apps.alerts.models import AlertType
from apps.inventory.models import Product
from apps.receivables.models import Receivable, ReceivableStatus

# Un producto "por vencer" vence dentro de estos días (los ya vencidos también cuentan).
EXPIRING_WINDOW_DAYS = 30

AlertKey = tuple[str, int]


def _alertable_products() -> QuerySet[Product]:
    return Product.objects.filter(deleted_at__isnull=True, is_active=True)


def _stock_conditions() -> dict[AlertKey, str]:
    products = _alertable_products()
    out_of_stock = {
        (AlertType.OUT_OF_STOCK, p.pk): f"{p.name} está agotado." for p in products.filter(current_stock__lte=0)
    }
    # Un agotado ya tiene su alerta: stock bajo es solo para el que aún tiene unidades.
    low = products.filter(minimum_stock__isnull=False, current_stock__gt=0, current_stock__lte=F("minimum_stock"))
    low_stock = {
        (AlertType.LOW_STOCK, p.pk): f"{p.name} tiene stock bajo: quedan {p.current_stock} (mínimo {p.minimum_stock})."
        for p in low
    }
    return out_of_stock | low_stock


def _expiry_conditions(today: date) -> dict[AlertKey, str]:
    limit = today + timedelta(days=EXPIRING_WINDOW_DAYS)
    expiring = _alertable_products().filter(expiration_date__isnull=False, expiration_date__lte=limit)
    return {
        (AlertType.EXPIRING, p.pk): (
            f"{p.name} {'venció' if p.expiration_date < today else 'vence'} el {p.expiration_date:%Y-%m-%d}."
        )
        for p in expiring
    }


def _receivable_conditions() -> dict[AlertKey, str]:
    overdue = Receivable.objects.filter(status=ReceivableStatus.OVERDUE, balance__gt=0).select_related("client")
    return {
        (AlertType.OVERDUE_RECEIVABLE, r.pk): f"El fiado de {r.client} está vencido; saldo {r.balance}."
        for r in overdue
    }


def current_conditions(today: date) -> dict[AlertKey, str]:
    return _stock_conditions() | _expiry_conditions(today) | _receivable_conditions()
