"""generate_alerts: creación por tipo (regla 48), idempotencia y resolución automática."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.alerts import services
from apps.alerts.conditions import EXPIRING_WINDOW_DAYS
from apps.alerts.models import Alert, AlertType
from apps.audit.models import AuditLog
from apps.cash import services as cash
from apps.inventory import services as inventory
from apps.receivables import services as receivables
from apps.receivables.models import ReceivableStatus
from apps.tenancy.models import Branch
from tests.alerts.helpers import TODAY, alert_for, make_overdue_debt, make_product, open_types

pytestmark = pytest.mark.django_db


def pay_debt(owner, debt):
    branch = Branch.objects.create(name="Centro")
    cash.open_session(owner, branch.public_id, Decimal("0"))
    receivables.add_payment(owner, debt.public_id, debt.balance, "efectivo", branch.public_id)


# ── Creación por tipo ────────────────────────────────────────────────────────


def test_agotado_y_stock_bajo_no_se_mezclan(owner):
    empty = make_product(owner, "Cera", stock=0, minimum_stock=3)
    low = make_product(owner, "Gel", stock=2, minimum_stock=3)
    enough = make_product(owner, "Talco", stock=5, minimum_stock=3)
    no_minimum = make_product(owner, "Aceite", stock=1)

    result = services.generate_alerts(TODAY)

    assert open_types(empty) == [AlertType.OUT_OF_STOCK]
    assert open_types(low) == [AlertType.LOW_STOCK]
    assert open_types(enough) == open_types(no_minimum) == []
    assert (result["created"][AlertType.OUT_OF_STOCK], result["created"][AlertType.LOW_STOCK]) == (1, 1)
    assert "quedan 2 (mínimo 3)" in alert_for(product=low).message


def test_por_vencer_dentro_de_la_ventana_e_incluye_vencidos(owner):
    soon = make_product(owner, "Tónico", stock=5, expiration_date=TODAY + timedelta(days=EXPIRING_WINDOW_DAYS))
    expired = make_product(owner, "Crema", stock=5, expiration_date=TODAY - timedelta(days=1))
    later = make_product(owner, "Loción", stock=5, expiration_date=TODAY + timedelta(days=EXPIRING_WINDOW_DAYS + 1))

    services.generate_alerts(TODAY)

    assert open_types(soon) == [AlertType.EXPIRING]
    assert "venció" in alert_for(product=expired).message
    assert open_types(later) == []


def test_fiado_vencido_se_marca_y_genera_alerta(owner):
    late = make_overdue_debt(owner)
    on_time = receivables.create_manual(owner, late.client.public_id, Decimal("1000"), due_date=TODAY + timedelta(5))

    result = services.generate_alerts(TODAY)

    late.refresh_from_db()
    on_time.refresh_from_db()
    assert (late.status, on_time.status, result["overdue_marked"]) == (
        ReceivableStatus.OVERDUE,
        ReceivableStatus.PENDING,
        1,
    )
    assert alert_for(receivable=late).alert_type == AlertType.OVERDUE_RECEIVABLE


def test_productos_borrados_o_inactivos_no_generan_alertas(owner):
    inventory.soft_delete_product(owner, make_product(owner, "Vieja").public_id)
    inventory.deactivate_product(owner, make_product(owner, "Pausada").public_id)
    services.generate_alerts(TODAY)
    assert not Alert.objects.exists()


def test_sin_barberia_activa_no_genera():
    with pytest.raises(RuntimeError):
        services.generate_alerts(TODAY)


# ── Idempotencia ─────────────────────────────────────────────────────────────


def test_correr_dos_veces_no_duplica(owner):
    make_product(owner, "Cera")
    make_overdue_debt(owner)
    services.generate_alerts(TODAY)

    second = services.generate_alerts(TODAY)

    assert (sum(second["created"].values()), second["resolved"]) == (0, 0)
    assert Alert.objects.count() == 2
    assert AuditLog.objects.filter(action="alertas.generar").count() == 1  # la segunda no hizo nada


def test_una_alerta_leida_sigue_abierta_y_no_se_duplica(owner, cashier):
    product = make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    services.mark_as_read(cashier, alert_for(product=product).public_id)

    assert sum(services.generate_alerts(TODAY)["created"].values()) == 0
    assert Alert.objects.filter(product=product).count() == 1


# ── Resolución automática ────────────────────────────────────────────────────


def test_reponer_el_stock_resuelve_agotado(owner):
    product = make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    inventory.register_entry(owner, product.public_id, 10, "Compra")

    result = services.generate_alerts(TODAY)

    assert result["resolved"] == 1
    assert alert_for(product=product).resolved_at is not None
    assert AuditLog.objects.filter(action="alertas.generar").latest("pk").after["resolved"] == 1


def test_pasar_de_stock_bajo_a_agotado_cambia_la_alerta(owner):
    product = make_product(owner, "Gel", stock=2, minimum_stock=3)
    services.generate_alerts(TODAY)
    inventory.register_adjustment(owner, product.public_id, -2, "Conteo")

    services.generate_alerts(TODAY)

    assert open_types(product) == [AlertType.OUT_OF_STOCK]
    assert Alert.objects.get(product=product, alert_type=AlertType.LOW_STOCK).resolved_at is not None


@pytest.mark.parametrize("change", ["borrado", "inactivo", "nueva_fecha"])
def test_un_producto_que_ya_no_aplica_resuelve_su_alerta(owner, change):
    product = make_product(owner, "Tónico", stock=5, expiration_date=TODAY + timedelta(days=3))
    services.generate_alerts(TODAY)
    if change == "borrado":
        inventory.soft_delete_product(owner, product.public_id)
    elif change == "inactivo":
        inventory.deactivate_product(owner, product.public_id)
    else:
        inventory.update_product(owner, product.public_id, {"expiration_date": TODAY + timedelta(days=90)})

    assert services.generate_alerts(TODAY)["resolved"] == 1


def test_pagar_el_fiado_resuelve_fiado_vencido(owner):
    debt = make_overdue_debt(owner)
    services.generate_alerts(TODAY)
    pay_debt(owner, debt)

    assert services.generate_alerts(TODAY)["resolved"] == 1
    assert alert_for(receivable=debt).resolved_at is not None


def test_anular_el_fiado_resuelve_fiado_vencido(owner):
    debt = make_overdue_debt(owner)
    services.generate_alerts(TODAY)
    receivables.cancel_receivable(owner, debt.public_id, "Error de digitación")
    assert services.generate_alerts(TODAY)["resolved"] == 1


def test_si_la_condicion_vuelve_se_crea_una_alerta_nueva(owner):
    product = make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    inventory.register_entry(owner, product.public_id, 2, "Compra")
    services.generate_alerts(TODAY)
    inventory.register_adjustment(owner, product.public_id, -2, "Venta sin registrar")

    result = services.generate_alerts(TODAY)

    assert result["created"][AlertType.OUT_OF_STOCK] == 1
    assert Alert.objects.filter(product=product).count() == 2
    assert open_types(product) == [AlertType.OUT_OF_STOCK]


def test_una_alerta_leida_se_resuelve_y_conserva_quien_la_leyo(owner, cashier):
    product = make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    read = services.mark_as_read(cashier, alert_for(product=product).public_id)
    inventory.register_entry(owner, product.public_id, 10, "Compra")

    assert services.generate_alerts(TODAY)["resolved"] == 1
    resolved = Alert.objects.get(pk=read.pk)
    assert resolved.resolved_at is not None
    assert (resolved.read_at, resolved.read_by) == (read.read_at, cashier)

    inventory.register_adjustment(owner, product.public_id, -10, "Conteo")
    services.generate_alerts(TODAY)
    new = Alert.objects.get(product=product, resolved_at__isnull=True)
    assert new.pk != read.pk and not new.is_read


def test_un_fiado_vencido_leido_se_resuelve_al_pagarlo(owner, cashier):
    debt = make_overdue_debt(owner)
    services.generate_alerts(TODAY)
    services.mark_as_read(cashier, alert_for(receivable=debt).public_id)
    pay_debt(owner, debt)

    assert services.generate_alerts(TODAY)["resolved"] == 1
    alert = alert_for(receivable=debt)
    assert alert.resolved_at is not None and alert.read_by == cashier
