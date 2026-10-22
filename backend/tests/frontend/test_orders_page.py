"""Pantalla de Comandas (fase F3): alcance, precios de la sede, cobro, anulación, descuento y consultas."""

from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.catalog.models import ServiceBranchPrice
from apps.sales import services as sales
from apps.sales.models import Order, OrderStatus, Payment
from apps.staff.models import BarberBranch
from apps.tenancy.models import Branch
from tests.conftest import scope_of
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db

D = Decimal


def _client(membership) -> Client:
    client = Client()
    client.force_login(membership.user)
    return client


def _notices(response) -> list[str]:
    return [str(message) for message in get_messages(response.wsgi_request)]


def _open_order(world, *, client=None, barber=None, service=None):
    """Una comanda abierta en Centro con un corte de Ana (o del barbero indicado), creada por el cajero."""
    scope = scope_of(world.cashier, world.branch)
    order = sales.create_order(world.cashier, scope, client=client, barber=barber or world.ana.public_id)
    sales.add_item(world.cashier, order.public_id, scope=scope, service=(service or world.corte).public_id)
    return order


@pytest.fixture
def norte_order(world):
    norte = Branch.objects.create(name="Norte")
    BarberBranch.objects.create(barber=world.beto, branch=norte)
    in_norte = scope_of(world.owner, norte)
    order = sales.create_order(world.owner, in_norte, barber=world.beto.public_id)
    sales.add_item(world.owner, order.public_id, scope=in_norte, service=world.barba.public_id)
    return order


def test_el_cajero_de_centro_no_ve_ni_abre_comandas_de_norte(world, norte_order):
    mine = _open_order(world)
    cashier = _client(world.cashier)

    listed = cashier.get(reverse("orders_board")).context["rows"]
    assert [row["order"].pk for row in listed] == [mine.pk]
    assert cashier.get(reverse("orders_detail", args=[norte_order.public_id])).status_code == 404
    response = cashier.post(reverse("orders_add_line", args=[norte_order.public_id]), {"item": "x"})
    assert response.status_code in (302, 404)
    assert norte_order.items.count() == 1


def test_el_barbero_solo_ve_sus_comandas(world):
    ana_order = _open_order(world, barber=world.ana.public_id)
    beto_order = _open_order(world, barber=world.beto.public_id)
    ana = _client(world.ana_login)

    rows = ana.get(reverse("orders_board")).context["rows"]

    assert [row["order"].pk for row in rows] == [ana_order.pk]
    assert ana.get(reverse("orders_detail", args=[beto_order.public_id])).status_code == 404


def test_el_precio_de_la_linea_sale_de_la_sede_aunque_el_formulario_mande_otro(world):
    ServiceBranchPrice.objects.create(service=world.barba, branch=world.branch, price=D("18000"))
    order = _open_order(world)
    data = {"item": f"servicio:{world.barba.public_id}", "cantidad": 1, "precio": "1", "unit_price": "1"}

    _client(world.cashier).post(reverse("orders_add_line", args=[order.public_id]), data)

    assert order.items.get(name="Barba").unit_price == D("18000")


def test_un_fiado_exige_un_cliente_registrado(world):
    order = _open_order(world)  # sin cliente

    response = _client(world.cashier).post(reverse("orders_checkout", args=[order.public_id]), {"metodo": "fiado"})

    order.refresh_from_db()
    assert order.status == OrderStatus.OPEN
    assert any("cliente" in notice for notice in _notices(response))


def test_el_efectivo_calcula_las_vueltas_y_registra_el_total(world):
    order = _open_order(world)  # corte de 25 000

    response = _client(world.cashier).post(
        reverse("orders_checkout", args=[order.public_id]), {"metodo": "efectivo", "recibido": "30000"}
    )

    assert Payment.objects.get(order=order).amount == D("25000")
    assert "Vueltas: $5.000." in " ".join(_notices(response))
    assert sales.cash_change(D("25000"), D("25000")) == 0
    with pytest.raises(Exception, match="no alcanza"):
        sales.cash_change(D("25000"), D("20000"))


def test_el_doble_envio_del_cobro_no_cobra_dos_veces(world):
    order = _open_order(world)
    cashier = _client(world.cashier)
    data = {"metodo": "efectivo", "recibido": "25000"}

    cashier.post(reverse("orders_checkout", args=[order.public_id]), data)
    second = cashier.post(reverse("orders_checkout", args=[order.public_id]), data)

    assert Payment.objects.filter(order=order).count() == 1
    assert any("no se puede modificar" in notice for notice in _notices(second))


def test_anular_y_descontar_exigen_su_permiso_y_quedan_en_la_auditoria(world):
    order = _open_order(world)
    barber = _client(world.ana_login)
    discount = {"monto": "5000", "motivo": "Cliente frecuente"}

    assert barber.post(reverse("orders_discount", args=[order.public_id]), discount).status_code == 403
    _client(world.cashier).post(reverse("orders_discount", args=[order.public_id]), discount)
    sales.checkout_order(
        world.cashier, order.public_id, scope=scope_of(world.cashier), checkout=sales.Checkout("efectivo", D("20000"))
    )
    cancel = {"motivo": "Error de cobro", "confirmar": "on"}
    assert _client(world.cashier).post(reverse("orders_cancel", args=[order.public_id]), cancel).status_code == 403
    logged_in_with_mfa(world.owner.user).post(reverse("orders_cancel", args=[order.public_id]), cancel)

    order.refresh_from_db()
    assert (order.discount, order.status) == (D("5000"), OrderStatus.CANCELLED)
    assert {"comanda.descontar", "comanda.anular"} <= set(AuditLog.objects.values_list("action", flat=True))


def test_en_todas_las_sedes_no_se_crea_una_comanda(world):
    owner = logged_in_with_mfa(world.owner.user)
    Branch.objects.create(name="Norte")
    owner.post(reverse("switch_branch"), {"sede": "todas"})
    before = Order.objects.count()

    response = owner.post(reverse("orders_create"), {})

    assert Order.objects.count() == before
    assert any("Elige una sede" in notice for notice in _notices(response))


# Sesión, alcance, marco, conteos de pestañas, la lista con sus líneas y pagos, y la barra del menú.
BOARD_QUERIES = 17


@pytest.mark.parametrize("orders", [1, 6])
def test_la_lista_no_crece_con_el_numero_de_comandas(world, django_assert_num_queries, orders):
    for _ in range(orders):
        _open_order(world)
    cashier = _client(world.cashier)

    with django_assert_num_queries(BOARD_QUERIES):
        cashier.get(reverse("orders_board"))
