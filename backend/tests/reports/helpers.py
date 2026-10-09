"""Ventas de prueba hechas con los services reales sobre el fixture `world`."""

from datetime import datetime
from zoneinfo import ZoneInfo

from apps.sales import services as sales
from apps.sales.models import Order

BOGOTA = ZoneInfo("America/Bogota")


def sell(w, barber, *, service=None, product=None, quantity=1, method="efectivo") -> Order:
    """Un registro rápido cobrado completo por el cajero."""
    return sales.quick_register(
        w.cashier,
        w.branch.public_id,
        barber.public_id,
        method,
        service=service and service.public_id,
        product=product and product.public_id,
        quantity=quantity,
    )


def close_at(order: Order, local: datetime) -> None:
    """Mueve el cierre a una hora local de Bogotá. Order no es solo-agregar, así que puede actualizarse."""
    Order.objects.filter(pk=order.pk).update(closed_at=local.replace(tzinfo=BOGOTA))
