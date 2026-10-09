"""Datos de prueba para las alertas: productos y fiados vencidos creados con los services reales."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.alerts.models import Alert
from apps.clients import services as clients
from apps.inventory import services as inventory
from apps.receivables import services as receivables

TODAY = timezone.localdate()


def make_product(owner, name, stock=0, **data):
    return inventory.create_product(owner, {"name": name, "product_type": "venta", **data}, initial_stock=stock)


def make_overdue_debt(owner, name="Laura"):
    client = clients.create_client(
        owner, {"full_name": name}, data_consent_at=timezone.now(), data_policy_version="2026-10"
    )
    return receivables.create_manual(owner, client.public_id, Decimal("30000"), due_date=TODAY - timedelta(days=1))


def alert_for(product=None, receivable=None) -> Alert:
    return Alert.objects.get(product=product, receivable=receivable)


def open_types(product) -> list[str]:
    alerts = Alert.objects.filter(product=product, resolved_at__isnull=True)
    return sorted(alerts.values_list("alert_type", flat=True))
