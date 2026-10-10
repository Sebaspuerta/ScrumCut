"""Cada lugar que escribe auditoría lo hace sin violar RLS, con un rol como el de producción.

La suite corre como superusuario, que ignora RLS; aquí cada escritura corre con el rol
sin privilegios y en el contexto en que ocurre de verdad: con la barbería activa (una
petición o la tarea de alertas) o, para cerrar sesiones, como evento de plataforma.
"""

from decimal import Decimal
from functools import partial

import pytest

from apps.accounts.services import logout_all_devices
from apps.alerts import services as alerts
from apps.alerts.models import Alert
from apps.audit.models import AuditLog
from apps.cash import services as cash
from apps.catalog import services as catalog
from apps.clients import services as clients
from apps.inventory import services as inventory
from apps.receivables import services as receivables
from apps.sales import services as sales
from apps.sales.selectors import local_today
from apps.staff import services as staff
from tests.rls_support import back_to_test_role, become_production_role, postgres_only

pytestmark = [pytest.mark.django_db, postgres_only]

D = Decimal
PLATFORM_EVENTS = {"sesion.cerrar_todas"}


def _out_of_stock(w):
    return inventory.create_product(w.owner, {"name": "Talco", "product_type": "venta"})


def _alert_to_read(w):
    product = _out_of_stock(w)
    alerts.generate_alerts(local_today(w.owner))
    return partial(alerts.mark_as_read, w.cashier, Alert.objects.get(product=product).public_id)


def _alerts_to_generate(w):
    _out_of_stock(w)
    return partial(alerts.generate_alerts, local_today(w.owner))


# Cada caso prepara sus datos con el rol de pruebas y devuelve la escritura que se audita.
CASES = {
    "servicio.crear": lambda w: partial(
        catalog.create_service, w.owner, name="Tinte", price=D("30000"), duration_minutes=40
    ),
    "barbero.crear": lambda w: partial(staff.create_barber, w.owner, {"display_name": "Caro"}, "percentage", 30),
    "cliente.crear": lambda w: partial(
        clients.create_client,
        w.owner,
        {"full_name": "Pedro"},
        data_consent_at=w.laura.data_consent_at,
        data_policy_version="2026-10",
    ),
    "producto.crear": lambda w: partial(inventory.create_product, w.owner, {"name": "Gel", "product_type": "venta"}),
    "caja.cerrar": lambda w: partial(cash.close_session, w.cashier, w.session.public_id, D("50000")),
    "comanda.crear": lambda w: partial(sales.create_order, w.cashier, w.branch.public_id),
    "fiado.crear": lambda w: partial(receivables.create_manual, w.cashier, w.laura.public_id, D("1000")),
    "alertas.generar": _alerts_to_generate,
    "alerta.marcar_leida": _alert_to_read,
    "sesion.cerrar_todas": lambda w: partial(logout_all_devices, w.ana_login.user),
}


@pytest.mark.parametrize("action", CASES)
def test_cada_lugar_que_audita_escribe_su_evento_con_el_rol_de_produccion(world, action):
    write = CASES[action](world)
    become_production_role()

    write()  # dentro de la barbería activa de `world`, como en una petición

    back_to_test_role()
    event = AuditLog.objects.filter(action=action).latest("pk")
    assert event.barbershop_id == (None if action in PLATFORM_EVENTS else world.shop.pk)
