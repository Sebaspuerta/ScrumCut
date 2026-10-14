"""cargar_demo: solo en desarrollo, y deja un tablero con datos."""

from datetime import date, datetime, timedelta
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.alerts.models import Alert
from apps.cash.models import CashSession
from apps.core.tenant_context import tenant_context
from apps.sales.models import Order, OrderStatus
from apps.tenancy.models import Barbershop

pytestmark = pytest.mark.django_db


def test_se_niega_a_correr_fuera_de_desarrollo():
    with pytest.raises(CommandError):
        call_command("cargar_demo")
    assert not Barbershop.objects.exists()


@override_settings(DEBUG=True)
def test_carga_ventas_cajas_y_alertas_y_no_se_repite():
    out = StringIO()
    call_command("cargar_demo", "--dias", "8", stdout=out)

    shop = Barbershop.objects.get(slug="demo")
    with tenant_context(shop.pk):
        closed_days = {order.closed_at.date() for order in Order.objects.filter(status=OrderStatus.CLOSED)}
        assert len(closed_days) >= 5  # 8 días menos el domingo
        assert CashSession.objects.filter(closed_at__isnull=False).count() >= 5
        assert Alert.objects.exists()
    assert "demo-dueno@scrumcut.test" in out.getvalue()

    with pytest.raises(CommandError):
        call_command("cargar_demo", stdout=StringIO())


def _demo_at(hour: int) -> Barbershop:
    """Miércoles 14 de octubre de 2026 a la hora dada en Bogotá."""
    moment = datetime(2026, 10, 14, hour, tzinfo=ZoneInfo("America/Bogota"))
    with override_settings(DEBUG=True), mock.patch("django.utils.timezone.now", return_value=moment):
        call_command("cargar_demo", "--dias", "3", stdout=StringIO())
    return Barbershop.objects.get(slug="demo")


def test_antes_de_la_apertura_no_hay_caja_ni_ventas_de_hoy():
    shop = _demo_at(7)
    with tenant_context(shop.pk):
        assert not CashSession.objects.filter(closed_at__isnull=True).exists()
        assert not Order.objects.filter(closed_at__date=date(2026, 10, 14)).exists()
        assert CashSession.objects.filter(closed_at__isnull=False).exists()  # los días anteriores sí


def test_a_mediodia_la_caja_esta_abierta_y_no_hay_ventas_posteriores():
    shop = _demo_at(12)
    noon = datetime(2026, 10, 14, 12, tzinfo=ZoneInfo("America/Bogota"))
    with tenant_context(shop.pk):
        assert CashSession.objects.filter(closed_at__isnull=True).exists()
        assert Order.objects.filter(closed_at__gte=noon - timedelta(hours=3)).exists()
        assert not Order.objects.filter(closed_at__gt=noon).exists()
