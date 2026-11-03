"""Cobro rápido en la API (regla 17): precio de la sede, barbero activo de la sede, sin cliente ni fiado, caja de
otro día, permisos, "todas" sin escrituras y un solo cobro por llave aunque lleguen dos envíos a la vez."""

import threading
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.api.exceptions import GENERIC_MESSAGES
from apps.api.order_serializers import NOT_IN_QUICK_CHARGE
from apps.cash.models import CashMovement, CashSession, MovementKind
from apps.cash.services import STALE_SESSION
from apps.catalog.branch_prices import set_branch_price
from apps.core.tenant_context import tenant_context
from apps.receivables.models import Receivable
from apps.sales.forms import PICK_ONE_ITEM
from apps.sales.models import Order, OrderStatus, Payment
from apps.sales.services.open_orders import BARBER_OTHER_BRANCH
from apps.staff import services as staff
from apps.tenancy import services as tenancy
from apps.tenancy.branch_scope import WRITE_NEEDS_ONE_BRANCH
from apps.tenancy.roles import Role
from tests.api.sales_support import choose_branch, post
from tests.concurrency import run_threads
from tests.conftest import scope_of, stock_of

pytestmark = pytest.mark.django_db

SHAPE = {"detail", "code", "field_errors"}


def _body(world, **changes) -> dict:
    """Un corte de Ana por Nequi, con una llave nueva."""
    body = {
        "request_key": str(uuid.uuid4()),
        "barber": str(world.ana.public_id),
        "service": str(world.corte.public_id),
        "method": "nequi",
    }
    return body | changes


def _charge(client: Client, body: dict):
    return post(client, "api_order_quick_charge", body)


def test_cobra_al_precio_de_la_sede_y_no_acepta_un_precio_del_cliente(world, norte, owner_client):
    set_branch_price(world.owner, world.corte, scope=scope_of(world.owner, norte), price=Decimal("30000"))
    choose_branch(owner_client, norte)

    charged = _charge(owner_client, _body(world))
    with_price = _charge(owner_client, _body(world, price="1"))

    assert charged.status_code == 201
    order = charged.json()
    assert (order["status"], order["total"], order["branch"], order["client"]) == (
        OrderStatus.CLOSED,
        "30000.00",
        "Norte",
        None,
    )
    assert [(payment["method"], payment["amount"]) for payment in order["payments"]] == [("Nequi", "30000.00")]
    assert (with_price.status_code, with_price.json()["field_errors"]) == (400, {"price": [NOT_IN_QUICK_CHARGE]})
    assert Order.objects.count() == 1


def test_un_producto_descuenta_el_stock_de_la_sede(world, cashier_client):
    response = _charge(cashier_client, _body(world, service=None, product=str(world.cera.public_id)))

    assert (response.status_code, response.json()["total"]) == (201, "20000.00")
    assert stock_of(world.cera, world.branch) == 4


def test_rechaza_un_barbero_inactivo_o_de_otra_sede(world, norte, cashier_client):
    staff.deactivate_barber(world.owner, world.beto.public_id)
    tenancy.set_barber_branches(world.owner, world.ana.public_id, branches=[norte.public_id])

    inactive = _charge(cashier_client, _body(world, barber=str(world.beto.public_id)))
    elsewhere = _charge(cashier_client, _body(world))

    assert inactive.status_code == 400
    assert inactive.json()["field_errors"] == {"barber": ["El barbero no existe o está inactivo."]}
    assert elsewhere.json()["field_errors"] == {"barber": [BARBER_OTHER_BRANCH]}
    assert not Order.objects.exists()


def test_rechaza_cliente_y_fiado(world, cashier_client):
    with_client = _charge(cashier_client, _body(world, client=str(world.laura.public_id)))
    as_credit = _charge(cashier_client, _body(world, method="fiado"))

    assert (with_client.status_code, with_client.json()["field_errors"]) == (400, {"client": [NOT_IN_QUICK_CHARGE]})
    assert as_credit.status_code == 400
    assert set(as_credit.json()["field_errors"]) == {"method"}
    assert not Order.objects.exists()
    assert not Receivable.objects.exists()


def test_una_caja_de_otro_dia_rechaza_el_cobro_en_efectivo(world, cashier_client):
    CashSession.objects.filter(pk=world.session.pk).update(opened_at=timezone.now() - timedelta(days=1))

    response = _charge(cashier_client, _body(world, method="efectivo"))

    assert response.status_code == 400
    assert set(response.json()) == SHAPE
    assert (response.json()["code"], response.json()["detail"]) == ("stale_session", STALE_SESSION)
    assert not Order.objects.exists()


def test_un_reenvio_con_la_misma_llave_devuelve_la_misma_comanda_sin_cobrar_otra(world, cashier_client):
    body = _body(world)

    first = _charge(cashier_client, body)
    again = _charge(cashier_client, body)

    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["id"] == first.json()["id"]
    assert (Order.objects.count(), Payment.objects.count()) == (1, 1)


def test_la_misma_llave_con_otros_datos_responde_409_sin_registrar_nada(world, cashier_client):
    body = _body(world)
    _charge(cashier_client, body)

    conflicts = [
        _charge(cashier_client, body | {"method": "efectivo"}),
        _charge(cashier_client, body | {"barber": str(world.beto.public_id)}),
        _charge(cashier_client, body | {"service": str(world.barba.public_id)}),
    ]

    assert [response.status_code for response in conflicts] == [409, 409, 409]
    assert conflicts[0].json() == {"detail": GENERIC_MESSAGES[409], "code": "conflict", "field_errors": {}}
    assert (Order.objects.count(), Payment.objects.count()) == (1, 1)


@pytest.mark.django_db(transaction=True)
def test_dos_envios_simultaneos_de_la_misma_llave_dan_un_solo_cobro(world):
    """Doble clic o un reintento de red: la restricción única de la llave deja pasar uno; el otro recibe esa comanda."""
    body = _body(world)
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def charge() -> None:
        try:
            client = Client()
            client.force_login(world.cashier.user)
            barrier.wait()
            statuses.append(_charge(client, body).status_code)
        finally:
            connection.close()

    run_threads([threading.Thread(target=charge, name=f"cobro-rapido-{number}") for number in range(2)])

    assert sorted(statuses) == [200, 201]
    with tenant_context(world.shop.pk):
        assert Order.objects.count() == 1
        assert Payment.objects.count() == 1
        assert CashMovement.objects.filter(kind=MovementKind.SALE).count() == 1


@pytest.mark.parametrize(("role", "expected"), [(Role.VIEWER, 403), (Role.BARBER, 201), (Role.CASHIER, 201)])
def test_cobra_quien_tiene_comandas_cerrar(world, member, role, expected):
    login = {Role.BARBER: world.ana_login, Role.CASHIER: world.cashier}.get(role) or member(role, world.shop)
    client = Client()
    client.force_login(login.user)

    assert _charge(client, _body(world)).status_code == expected


def test_en_todas_las_sedes_no_se_cobra(world, norte, owner_client):
    assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200

    response = _charge(owner_client, _body(world))

    assert (response.status_code, response.json()["detail"]) == (400, WRITE_NEEDS_ONE_BRANCH)
    assert not Order.objects.exists()


def test_el_cobro_exige_csrf(world):
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)
    body = _body(world)

    rejected = _charge(client, body)
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(
        reverse("api_order_quick_charge"), body, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )

    assert (rejected.status_code, set(rejected.json())) == (403, SHAPE)
    assert accepted.status_code == 201


@pytest.mark.parametrize("item", [{"service": None}, {"product": "00000000-0000-0000-0000-000000000001"}])
def test_sin_item_o_con_dos_el_mensaje_sale_del_formulario_del_servidor(world, cashier_client, item):
    response = _charge(cashier_client, _body(world, **item))

    assert (response.status_code, response.json()["field_errors"]) == (400, {"item": [PICK_ONE_ITEM]})
    assert not Order.objects.exists()
