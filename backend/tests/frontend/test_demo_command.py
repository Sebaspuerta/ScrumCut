"""cargar_demo: solo en desarrollo, y deja un tablero con datos."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone

from apps.alerts.models import Alert, AlertType
from apps.cash.models import CashSession
from apps.core.tenant_context import tenant_context
from apps.inventory.models import MovementType, StockLevel, StockMovement
from apps.sales.models import Order, OrderItem, OrderStatus
from apps.tenancy.models import Barbershop

pytestmark = pytest.mark.django_db

D = Decimal


def test_se_niega_a_correr_fuera_de_desarrollo():
    with pytest.raises(CommandError):
        call_command("cargar_demo")
    assert not Barbershop.objects.exists()


BOGOTA = ZoneInfo("America/Bogota")


def _demo_at(hour: int, out: StringIO | None = None) -> Barbershop:
    """Miércoles 14 de octubre de 2026 a la hora dada en Bogotá: lunes y martes completos y hoy hasta esa hora."""
    moment = datetime(2026, 10, 14, hour, tzinfo=BOGOTA)
    with override_settings(DEBUG=True), mock.patch("django.utils.timezone.now", return_value=moment):
        call_command("cargar_demo", "--dias", "3", stdout=out or StringIO())
    return Barbershop.objects.get(slug="demo")


def test_carga_ventas_cajas_y_alertas_y_no_se_repite():
    out = StringIO()
    shop = _demo_at(12, out)  # con la hora fija, el resultado no depende del día en que corre la prueba

    with tenant_context(shop.pk):
        closed = Order.objects.filter(status=OrderStatus.CLOSED)
        closed_days = {timezone.localtime(order.closed_at, BOGOTA).date() for order in closed}
        assert closed_days == {date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 14)}
        assert CashSession.objects.filter(closed_at__isnull=False).count() == 4  # lunes y martes, en las 2 sedes
        assert Alert.objects.exists()
        cuts = OrderItem.objects.filter(service__name="Corte")
        assert set(cuts.filter(order__branch__name="Norte").values_list("unit_price", flat=True)) == {D("28000")}
        assert set(cuts.filter(order__branch__name="Centro").values_list("unit_price", flat=True)) == {D("25000")}
    assert "demo-dueno@scrumcut.test" in out.getvalue()

    with override_settings(DEBUG=True), pytest.raises(CommandError):
        call_command("cargar_demo", stdout=StringIO())


def test_cada_sede_tiene_su_stock_con_un_traslado_y_un_stock_bajo_solo_en_norte():
    shop = _demo_at(12)
    with tenant_context(shop.pk):
        cera = dict(StockLevel.objects.filter(product__name="Cera mate").values_list("branch__name", "quantity"))
        transfers = StockMovement.objects.filter(movement_type=MovementType.TRANSFER_OUT)
        low = Alert.objects.filter(alert_type=AlertType.LOW_STOCK, resolved_at__isnull=True)

        assert cera["Centro"] != cera["Norte"]
        assert transfers.count() == 1
        assert StockMovement.objects.filter(transfer_id=transfers.get().transfer_id).count() == 2
        assert set(low.values_list("branch__name", flat=True)) == {"Norte"}


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
