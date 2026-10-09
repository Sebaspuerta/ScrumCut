"""Leer y marcar alertas: permisos (defecto 30), auditoría (defecto 31), selectores y aislamiento."""

import pytest
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.alerts import selectors, services
from apps.alerts.models import Alert
from apps.audit.models import AuditLog
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.tenancy.roles import Role
from tests.alerts.helpers import TODAY, alert_for, make_overdue_debt, make_product

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN, Role.CASHIER])
def test_marcar_como_leida_deja_auditoria(member, in_shop, owner, role):
    make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    reader = owner if role == Role.OWNER else member(role, in_shop)
    alert = Alert.objects.get()

    services.mark_as_read(reader, alert.public_id)
    services.mark_as_read(reader, alert.public_id)  # repetir no cambia nada ni audita de nuevo

    alert.refresh_from_db()
    assert alert.is_read and alert.read_by == reader
    log = AuditLog.objects.get(action="alerta.marcar_leida")
    assert (log.actor, log.entity_id) == (reader.user, str(alert.public_id))
    assert (log.before["read_at"], log.after["read_by"]) == (None, str(reader.public_id))


@pytest.mark.parametrize("role", [Role.BARBER, Role.VIEWER])
def test_barbero_y_consultor_no_marcan(member, in_shop, owner, role):
    make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    alert = Alert.objects.get()
    with pytest.raises(PermissionDenied):
        services.mark_as_read(member(role, in_shop), alert.public_id)
    alert.refresh_from_db()
    assert not alert.is_read


def test_lista_no_leidas_primero_sin_resueltas_y_conteo(owner, cashier):
    cera, gel, talco = (make_product(owner, name) for name in ("Cera", "Gel", "Talco"))
    services.generate_alerts(TODAY)
    services.mark_as_read(cashier, alert_for(product=cera).public_id)
    inventory.register_entry(owner, talco.public_id, 5, "Compra")
    services.generate_alerts(TODAY)  # resuelve la de Talco; la de Cera, leída y aún agotada, sigue abierta

    page = selectors.list_alerts(cashier)
    assert [(alert.product, alert.is_read) for alert in page] == [(gel, False), (cera, True)]
    assert selectors.unread_count(cashier) == 1  # ni la leída ni la resuelta cuentan
    assert selectors.list_alerts(cashier, unread_only=True).paginator.count == 1
    assert selectors.list_alerts(cashier, page_size=1).has_next()


def test_marcar_una_alerta_resuelta_no_hace_nada(owner, cashier):
    product = make_product(owner, "Cera")
    services.generate_alerts(TODAY)
    inventory.register_entry(owner, product.public_id, 10, "Compra")
    services.generate_alerts(TODAY)

    alert = services.mark_as_read(cashier, alert_for(product=product).public_id)

    assert not alert.is_read
    assert not AuditLog.objects.filter(action="alerta.marcar_leida").exists()


def test_leer_alertas_no_escribe(owner, cashier):
    make_product(owner, "Cera")
    make_overdue_debt(owner)
    with CaptureQueriesContext(connection) as queries:
        list(selectors.list_alerts(cashier))
        selectors.unread_count(cashier)
    writes = [q["sql"] for q in queries.captured_queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE"))]
    assert writes == []
    assert not Alert.objects.exists()


def test_el_consultor_lee_y_el_barbero_no(member, in_shop):
    assert selectors.unread_count(member(Role.VIEWER, in_shop)) == 0
    with pytest.raises(PermissionDenied):
        selectors.list_alerts(member(Role.BARBER, in_shop))


def test_cada_barberia_ve_y_marca_solo_sus_alertas(member, shop, other_shop):
    with tenant_context(shop.pk):
        make_product(member(Role.OWNER, shop), "Cera")
        services.generate_alerts(TODAY)
        mine = Alert.objects.get()
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        services.generate_alerts(TODAY)  # en su barbería no hay nada que alertar ni resolver
        assert selectors.unread_count(theirs) == 0
        with pytest.raises(Alert.DoesNotExist):
            services.mark_as_read(theirs, mine.public_id)
    with tenant_context(shop.pk):
        mine.refresh_from_db()
        assert mine.resolved_at is None
