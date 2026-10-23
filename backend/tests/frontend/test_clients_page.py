"""Pantalla de Clientes (fase F4): alcance por sede, búsqueda, enmascarado, duplicados, edición y consultas."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clients import services as clients
from apps.clients.models import Client as Customer
from apps.clients.profile import level_progress
from apps.sales import services as sales
from apps.sales.models import Order
from apps.staff.models import BarberBranch
from apps.tenancy.models import BarbershopSettings, Branch
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db

D = Decimal


def _client(membership) -> Client:
    client = Client()
    client.force_login(membership.user)
    return client


def _laura_row(response):
    return next(row for row in response.context["page"] if row.full_name == "Laura Gómez")


def _visit(world, customer) -> None:
    """Una barba cobrada por Nequi en Centro para ese cliente."""
    scope = scope_of(world.cashier)
    order = sales.create_order(world.cashier, scope, client=customer.public_id, barber=world.ana.public_id)
    sales.add_item(world.cashier, order.public_id, scope=scope, service=world.barba.public_id)
    sales.checkout_order(world.cashier, order.public_id, scope=scope, checkout=sales.Checkout.whole("nequi"))


@pytest.fixture
def laura_in_norte(world):
    """Laura se atiende en Norte con una barba fiada: visita y deuda solo de Norte."""
    norte = Branch.objects.create(name="Norte")
    BarberBranch.objects.create(barber=world.ana, branch=norte)
    in_norte = scope_of(world.owner, norte)
    order = sales.create_order(world.owner, in_norte, client=world.laura.public_id, barber=world.ana.public_id)
    sales.add_item(world.owner, order.public_id, scope=in_norte, service=world.barba.public_id)
    sales.close_order(world.owner, order.public_id, scope=in_norte, as_credit=True)
    return norte


def test_el_cajero_de_centro_no_ve_el_historial_ni_la_deuda_de_norte(world, laura_in_norte):
    cashier = _client(world.cashier)

    listed = [row.full_name for row in cashier.get(reverse("clients_board")).context["page"]]
    found = _laura_row(cashier.get(reverse("clients_board"), {"q": "Laura"}))
    card_page = cashier.get(reverse("clients_detail", args=[world.laura.public_id]))

    assert "Laura Gómez" not in listed  # sin búsqueda, la lista es la de Centro
    assert (found.level, found.visits, found.debt) == (
        "sin_sede",
        0,
        0,
    )  # la búsqueda la encuentra, sin cifras de Norte
    assert card_page.context["card"] == {"client": world.laura, "has_activity": False}
    html = card_page.content.decode().split('id="t-ficha"')[1]  # solo la ficha
    assert "Sin historial en esta sede" in html and "Deudor" not in html and "$15.000" not in html
    owner_card = logged_in_with_mfa(world.owner.user)
    owner_card.post(reverse("switch_branch"), {"sede": str(laura_in_norte.public_id)})
    assert owner_card.get(reverse("clients_detail", args=[world.laura.public_id])).context["card"]["visits"] == 1


@pytest.mark.parametrize("term", ["3001234567", "300 123 4567", "Laura"])
def test_la_busqueda_por_celular_encuentra_con_o_sin_espacios(world, term):
    rows = _client(world.cashier).get(reverse("clients_board"), {"q": term}).context["page"]
    assert [row.full_name for row in rows] == ["Laura Gómez"]


def test_el_celular_sale_enmascarado(world):
    html = _client(world.cashier).get(reverse("clients_detail", args=[world.laura.public_id])).content.decode()
    assert "300 *** 4567" in html
    assert "3001234567" not in html


def test_un_duplicado_se_detecta_y_solo_muestra_el_nombre(world, legal_documents):
    data = {"full_name": "Otra persona", "phone": "300 123 4567", "consent": "on"}

    response = _client(world.cashier).post(reverse("clients_new"), data)

    assert response.context["duplicate"].pk == world.laura.pk
    assert Customer.objects.filter(full_name="Otra persona").count() == 0


def test_un_celular_que_no_es_colombiano_se_rechaza(world, legal_documents):
    data = {"full_name": "Pedro", "phone": "12345", "consent": "on"}
    response = _client(world.cashier).post(reverse("clients_new"), data)
    assert "celular colombiano" in response.content.decode()


def test_editar_exige_permiso_y_queda_en_la_auditoria(world, member, in_shop):
    url = reverse("clients_edit", args=[world.laura.public_id])
    viewer = _client(member(Role.VIEWER, in_shop))
    assert viewer.post(url, {"full_name": "Hackeada"}).status_code == 403

    _client(world.cashier).post(url, {"full_name": "Laura Gómez Ruiz", "notes": "Corte bajo a los lados"})

    world.laura.refresh_from_db()
    assert (world.laura.full_name, world.laura.phone) == ("Laura Gómez Ruiz", "573001234567")  # el celular no cambia
    log = AuditLog.objects.get(action="cliente.editar")
    assert (log.before["full_name"], log.after["full_name"]) == ("Laura Gómez", "Laura Gómez Ruiz")


def test_nueva_comanda_para_el_cliente_abre_la_comanda_con_el_cliente(world):
    response = _client(world.cashier).post(reverse("orders_create"), {"cliente": str(world.laura.public_id)})

    order = Order.objects.get()
    assert order.client == world.laura
    assert response["Location"] == reverse("orders_detail", args=[order.public_id])


def test_el_progreso_de_nivel_usa_los_umbrales_del_backend(world):
    settings = BarbershopSettings.objects.get()  # frecuente desde 3 visitas, VIP desde 10
    assert level_progress(1, settings) == {"next": "Frecuente", "missing": 2, "percent": 33}
    assert level_progress(5, settings) == {"next": "VIP", "missing": 5, "percent": 50}
    assert level_progress(10, settings)["next"] is None

    order = sales.create_order(
        world.cashier, scope_of(world.cashier), client=world.laura.public_id, barber=world.ana.public_id
    )
    sales.add_item(world.cashier, order.public_id, scope=scope_of(world.cashier), service=world.barba.public_id)
    sales.checkout_order(
        world.cashier, order.public_id, scope=scope_of(world.cashier), checkout=sales.Checkout.whole("nequi")
    )
    card = _client(world.cashier).get(reverse("clients_detail", args=[world.laura.public_id])).context["card"]
    assert (card["visits"], card["progress"]["missing"]) == (1, settings.frequent_min_visits - 1)


# Sesión, alcance, marco, conteo por nivel, la página con sus cifras por subconsulta y las cuatro cifras.
LIST_QUERIES = 20


@pytest.mark.parametrize("extra", [1, 7])
def test_la_lista_no_crece_con_el_numero_de_clientes(world, django_assert_num_queries, extra):
    for number in range(extra):
        new = clients.create_client(
            world.owner, {"full_name": f"Cliente {number}"}, data_consent_at=timezone.now(), data_policy_version="1"
        )
        _visit(world, new)  # con una visita en Centro, sale en la lista de la sede
    cashier = _client(world.cashier)
    with django_assert_num_queries(LIST_QUERIES):
        response = cashier.get(reverse("clients_board"))
    assert len(response.context["page"]) == extra


# La lista más la ficha: perfil, nivel, barbero y servicio favoritos, últimas visitas y su deuda.
CARD_QUERIES = 32


@pytest.mark.parametrize("visits", [1, 4])
def test_la_ficha_no_crece_con_el_numero_de_visitas(world, django_assert_num_queries, visits):
    for _ in range(visits):
        order = sales.create_order(
            world.cashier, scope_of(world.cashier), client=world.laura.public_id, barber=world.ana.public_id
        )
        sales.add_item(world.cashier, order.public_id, scope=scope_of(world.cashier), service=world.barba.public_id)
        sales.add_item(world.cashier, order.public_id, scope=scope_of(world.cashier), product=world.cera.public_id)
        sales.checkout_order(
            world.cashier, order.public_id, scope=scope_of(world.cashier), checkout=sales.Checkout.whole("nequi")
        )
    cashier = _client(world.cashier)
    with django_assert_num_queries(CARD_QUERIES):
        cashier.get(reverse("clients_detail", args=[world.laura.public_id]))


def test_en_todas_el_nivel_dice_que_varia_por_sede(world):
    owner = logged_in_with_mfa(world.owner.user)
    Branch.objects.create(name="Norte")
    owner.post(reverse("switch_branch"), {"sede": "todas"})
    _visit(world, world.laura)
    assert "Varía por sede" in owner.get(reverse("clients_board")).content.decode()
