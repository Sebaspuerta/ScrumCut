"""Perfil de cliente (regla 47) leído de comandas cerradas y fiados."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.clients import services as clients
from apps.clients.selectors import ClientStatus, client_profile
from apps.receivables import services as receivables
from apps.sales import services as sales
from apps.sales.models import Order

pytestmark = pytest.mark.django_db

D = Decimal


def _visit(w, client, service, amount):
    order = sales.create_order(w.cashier, w.branch.public_id, client=client.public_id, barber=w.ana.public_id)
    sales.add_item(w.cashier, order.public_id, service=service.public_id)
    return sales.close_order(w.cashier, order.public_id, [{"method": "efectivo", "amount": amount}])


def _client(w, name):
    return clients.create_client(
        w.owner, {"full_name": name}, data_consent_at=timezone.now(), data_policy_version="2026-10"
    )


def test_cliente_sin_visitas_es_nuevo(world):
    profile = client_profile(world.cashier, world.laura.public_id)
    assert (profile["visits"], profile["spent"], profile["last_visit"], profile["balance"]) == (0, D("0"), None, D("0"))
    assert profile["status"] == ClientStatus.NEW


def test_frecuente_con_tres_visitas(world):
    for _ in range(3):
        _visit(world, world.laura, world.barba, "15000")
    profile = client_profile(world.cashier, world.laura.public_id)
    assert (profile["visits"], profile["spent"], profile["status"]) == (3, D("45000"), ClientStatus.FREQUENT)


def test_vip_por_gasto(world):
    for _ in range(8):
        _visit(world, world.laura, world.corte, "25000")
    profile = client_profile(world.cashier, world.laura.public_id)
    assert (profile["spent"], profile["status"]) == (D("200000"), ClientStatus.VIP)


def test_inactivo_sin_visitas_recientes(world):
    order = _visit(world, world.laura, world.barba, "15000")
    Order.objects.filter(pk=order.pk).update(closed_at=timezone.now() - timedelta(days=91))
    assert client_profile(world.cashier, world.laura.public_id)["status"] == ClientStatus.INACTIVE


def test_deudor_manda_sobre_lo_demas(world):
    pedro = _client(world, "Pedro Ruiz")
    for _ in range(3):
        _visit(world, pedro, world.barba, "15000")
    receivables.create_manual(world.cashier, pedro.public_id, D("7000"))
    profile = client_profile(world.cashier, pedro.public_id)
    assert (profile["balance"], profile["status"]) == (D("7000"), ClientStatus.DEBTOR)


def test_las_comandas_anuladas_no_cuentan(world):
    order = _visit(world, world.laura, world.barba, "15000")
    sales.cancel_order(world.owner, order.public_id, "Error")
    assert client_profile(world.cashier, world.laura.public_id)["visits"] == 0
