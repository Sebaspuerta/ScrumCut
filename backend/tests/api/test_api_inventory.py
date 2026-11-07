"""Inventario en la API (fase R7): el catálogo con la existencia y el precio de la sede, sus filtros, categorías,
alcance de sede, aislamiento entre barberías, permisos por rol, CSRF y el formato único de error."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.api.exceptions import GENERIC_MESSAGES
from apps.catalog.branch_prices import set_branch_price
from apps.core.tenant_context import tenant_context
from apps.inventory import services
from apps.inventory.models import Product, ProductCategory, StockLevel
from apps.sales.selectors import local_today
from apps.tenancy.branch_scope import WRITE_NEEDS_ONE_BRANCH
from apps.tenancy.roles import Role
from tests.api.inventory_support import entry, product_url
from tests.api.sales_support import choose_branch, post
from tests.conftest import scope_of, stock_of
from tests.frontend.conftest import logged_in_with_mfa
from tests.inventory.helpers import make_product

pytestmark = pytest.mark.django_db

SHAPE = {"detail", "code", "field_errors"}


def _list(client: Client, **query) -> dict:
    response = client.get(reverse("api_products"), query)
    assert response.status_code == 200
    return response.json()


def _rows(client: Client, **query) -> dict[str, dict]:
    return {row["name"]: row for row in _list(client, **query)["results"]}


def _detail(client: Client, product: Product, **query):
    return client.get(product_url("api_product", product), query)


def _new_product(**changes) -> dict:
    body = {
        "name": "Pomada",
        "category": None,
        "product_type": "venta",
        "purchase_cost": "9000",
        "sale_price": "18000",
        "minimum_stock": 2,
        "expiration_date": None,
        "supplier": "Proveedor Sur",
        "initial_stock": 4,
    }
    return body | changes


@pytest.fixture
def todas(owner_client, norte) -> Client:
    assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200
    return owner_client


# ── Lista y detalle por el alcance ───────────────────────────────────────────


def test_la_lista_trae_la_existencia_y_el_precio_efectivo_de_cada_sede(world, norte, owner_client):
    set_branch_price(world.owner, world.cera, scope=scope_of(world.owner, norte), price=Decimal("22000"))

    choose_branch(owner_client, norte)
    in_norte = _rows(owner_client)["Cera"]
    choose_branch(owner_client, world.branch)
    in_centro = _rows(owner_client)["Cera"]

    assert (in_norte["stock"], in_norte["price"], in_norte["levels"]) == (
        3,
        "22000.00",
        [{"branch": "Norte", "quantity": 3, "low": False}],
    )
    assert (in_centro["stock"], in_centro["price"]) == (5, "20000.00")


def test_en_todas_trae_la_suma_cada_sede_y_el_precio_del_catalogo(world, norte, todas):
    set_branch_price(world.owner, world.cera, scope=scope_of(world.owner, norte), price=Decimal("22000"))

    cera = _rows(todas)["Cera"]

    assert (cera["stock"], cera["price"]) == (8, "20000.00")
    assert [(level["branch"], level["quantity"]) for level in cera["levels"]] == [("Centro", 5), ("Norte", 3)]


def test_el_cajero_de_centro_no_ve_el_stock_ni_los_movimientos_de_norte(world, norte, cashier_client):
    cera = _rows(cashier_client)["Cera"]
    detail = _detail(cashier_client, world.cera).json()
    to_norte = post(cashier_client, "api_branch", {"sede": str(norte.public_id)})

    assert (cera["stock"], [level["branch"] for level in cera["levels"]]) == (5, ["Centro"])
    assert {movement["branch"] for movement in detail["movements"]["results"]} == {"Centro"}
    assert (detail["destinations"], detail["actions"]["adjust"]) == ([], False)
    assert to_norte.status_code == 403


def test_el_aviso_de_stock_bajo_compara_cada_sede_con_el_minimo(world, norte, owner_client):
    services.update_product(world.owner, world.cera.public_id, data={"minimum_stock": 4})

    choose_branch(owner_client, world.branch)
    centro = _rows(owner_client)["Cera"]
    choose_branch(owner_client, norte)
    in_norte = _rows(owner_client)["Cera"]

    assert (centro["low_stock"], in_norte["low_stock"]) == (False, True)


def test_los_filtros_por_busqueda_categoria_tipo_y_estado(world, owner_client):
    care = services.create_category(world.owner, name="Cuidado")
    services.update_product(world.owner, world.cera.public_id, data={"category": care.public_id, "supplier": "Sur"})
    services.deactivate_product(world.owner, world.cuchilla.public_id)

    assert set(_rows(owner_client)) == {"Cera"}
    assert set(_rows(owner_client, estado="inactivos")) == {"Cuchilla"}
    assert set(_rows(owner_client, estado="todos", categoria="sin")) == {"Cuchilla"}
    assert set(_rows(owner_client, estado="todos", categoria=str(care.public_id))) == {"Cera"}
    assert set(_rows(owner_client, estado="todos", tipo="consumible")) == {"Cuchilla"}
    assert set(_rows(owner_client, q="sur")) == {"Cera"}
    assert _list(owner_client, categoria="no-es-un-id")["category"] == ""


def test_el_detalle_trae_el_historial_paginado_con_lo_mas_reciente_primero(world, owner_client):
    for quantity in range(1, 22):
        entry(owner_client, world.cera, quantity=quantity)

    first, second = _detail(owner_client, world.cera).json(), _detail(owner_client, world.cera, page=2).json()

    assert (first["movements"]["count"], first["movements"]["pages"]) == (22, 2)
    assert first["movements"]["results"][0]["quantity"] == 21
    assert [movement["reason"] for movement in second["movements"]["results"]] == ["Compra", "Inventario inicial"]


# ── Aislamiento entre barberías ──────────────────────────────────────────────


def test_una_barberia_no_ve_ni_toca_los_productos_de_otra(world, owner_client, member, other_shop):
    with tenant_context(other_shop.pk):
        theirs = make_product(member(Role.OWNER, other_shop), name="Cera ajena", initial_stock=3)

    assert "Cera ajena" not in _rows(owner_client, estado="todos")
    assert _detail(owner_client, theirs).status_code == 404
    assert post(owner_client, "api_product_edit", _new_product(), public_id=theirs.public_id).status_code == 404
    assert entry(owner_client, theirs).status_code == 404
    with tenant_context(other_shop.pk):
        assert stock_of(Product.objects.get(pk=theirs.pk)) == 3


# ── Crear, editar, activar y borrar ──────────────────────────────────────────


def test_crear_deja_el_stock_inicial_en_la_sede_del_alcance(world, owner_client):
    response = post(owner_client, "api_product_create", _new_product())

    assert response.status_code == 201
    product = Product.objects.get(public_id=response.json()["id"])
    assert (response.json()["stock"], stock_of(product, world.branch)) == (4, 4)
    assert response.json()["movements"]["results"][0]["reason"] == "Inventario inicial"


def test_en_todas_se_crea_sin_stock_pero_no_con_stock(world, todas):
    with_stock = post(todas, "api_product_create", _new_product())
    without = post(todas, "api_product_create", _new_product(initial_stock=0))

    assert (with_stock.status_code, with_stock.json()["detail"]) == (400, WRITE_NEEDS_ONE_BRANCH)
    assert without.status_code == 201
    assert not StockLevel.objects.filter(product__name="Pomada").exists()


def test_el_dinero_no_llega_como_float_y_los_errores_van_por_campo(world, owner_client):
    as_float = post(owner_client, "api_product_create", _new_product(purchase_cost=9000.5))
    duplicate = post(owner_client, "api_product_create", _new_product(name="cera"))

    assert as_float.status_code == 400
    assert set(as_float.json()) == SHAPE
    assert list(as_float.json()["field_errors"]) == ["purchase_cost"]
    assert duplicate.json()["detail"] == "Ya existe un producto con ese nombre."
    assert Product.objects.filter(name="Pomada").count() == 0


def test_editar_desactivar_y_borrar(world, owner_client):
    edited = post(owner_client, "api_product_edit", _new_product(name="Cera mate"), public_id=world.cera.public_id)
    inactive = post(owner_client, "api_product_active", {"active": False}, public_id=world.cera.public_id)
    deleted = post(owner_client, "api_product_delete", public_id=world.cera.public_id)

    assert (edited.status_code, edited.json()["name"], edited.json()["stock"]) == (200, "Cera mate", 5)
    assert inactive.json()["is_active"] is False
    assert deleted.json() == {"id": str(world.cera.public_id)}
    assert _detail(owner_client, world.cera).status_code == 404


# ── Categorías ───────────────────────────────────────────────────────────────


def test_categorias_crear_renombrar_y_borrar_con_o_sin_sus_productos(world, owner_client):
    created = post(owner_client, "api_inventory_category_create", {"name": "Cuidado"})
    care = ProductCategory.objects.get(name="Cuidado")
    renamed = post(owner_client, "api_inventory_category_edit", {"name": "Cuidado capilar"}, public_id=care.public_id)
    services.update_product(world.owner, world.cera.public_id, data={"category": care.public_id})
    tools = services.create_category(world.owner, name="Herramientas")
    services.update_product(world.owner, world.cuchilla.public_id, data={"category": tools.public_id})

    kept = post(owner_client, "api_inventory_category_delete", {"delete_products": False}, public_id=care.public_id)
    gone = post(owner_client, "api_inventory_category_delete", {"delete_products": True}, public_id=tools.public_id)

    assert [category["name"] for category in created.json()["results"]] == ["Cuidado"]
    assert [category["name"] for category in renamed.json()["results"]] == ["Cuidado capilar"]
    assert (kept.json()["results"], gone.json()["results"]) == (
        [{"id": str(tools.public_id), "name": "Herramientas"}],
        [],
    )
    assert Product.objects.get(pk=world.cera.pk).category is None
    assert Product.objects.get(pk=world.cuchilla.pk).deleted_at is not None


def test_una_categoria_repetida_responde_su_mensaje(world, owner_client):
    post(owner_client, "api_inventory_category_create", {"name": "Cuidado"})

    again = post(owner_client, "api_inventory_category_create", {"name": "cuidado"})

    assert (again.status_code, again.json()["detail"]) == (400, "Ya existe una categoría con ese nombre.")


# ── Precio por sede ──────────────────────────────────────────────────────────


def test_el_precio_de_la_sede_rige_y_al_quitarlo_vuelve_el_del_catalogo(world, norte, owner_client):
    choose_branch(owner_client, norte)

    fixed = post(owner_client, "api_product_branch_price", {"price": "22000"}, public_id=world.cera.public_id)
    removed = post(owner_client, "api_product_branch_price_remove", public_id=world.cera.public_id)

    assert (fixed.json()["price"], fixed.json()["branch_price"], fixed.json()["sale_price"]) == (
        "22000.00",
        "22000.00",
        "20000.00",
    )
    assert (removed.json()["price"], removed.json()["branch_price"]) == ("20000.00", None)


def test_en_todas_no_se_fija_un_precio_de_sede(world, todas):
    response = post(todas, "api_product_branch_price", {"price": "22000"}, public_id=world.cera.public_id)

    assert (response.status_code, response.json()["detail"]) == (400, WRITE_NEEDS_ONE_BRANCH)


# ── Avisos ───────────────────────────────────────────────────────────────────


def test_los_avisos_traen_el_stock_bajo_y_lo_que_vence_de_la_sede(world, owner_client):
    services.update_product(world.owner, world.cera.public_id, data={"minimum_stock": 6})
    soon = local_today(world.owner) + timedelta(days=10)
    make_product(world.owner, name="Tónico", product_type="perecedero", initial_stock=2, expiration_date=soon)
    make_product(
        world.owner,
        name="Loción",
        product_type="perecedero",
        initial_stock=1,
        expiration_date=soon - timedelta(days=30),
    )

    alerts = owner_client.get(reverse("api_inventory_alerts")).json()

    assert [(item["name"], item["quantity"], item["minimum_stock"]) for item in alerts["low_stock"]] == [("Cera", 5, 6)]
    assert [(item["name"], item["expired"]) for item in alerts["expiring"]] == [("Loción", True), ("Tónico", False)]
    assert (alerts["low_stock_count"], alerts["expiring_count"]) == (1, 2)


# ── Permisos, CSRF y errores ─────────────────────────────────────────────────


@pytest.mark.parametrize(("role", "expected"), [(Role.VIEWER, 403), (Role.CASHIER, 403), (Role.ADMIN, 201)])
def test_crea_quien_tiene_inventario_crear(world, member, role, expected):
    login = world.cashier if role == Role.CASHIER else member(role, world.shop)
    client = logged_in_with_mfa(login.user)

    assert post(client, "api_product_create", _new_product()).status_code == expected


@pytest.mark.parametrize(("role", "expected"), [(Role.ADMIN, 403), (Role.OWNER, 200)])
def test_borrar_es_solo_del_dueno(world, member, role, expected):
    login = world.owner if role == Role.OWNER else member(role, world.shop)
    client = logged_in_with_mfa(login.user)

    assert post(client, "api_product_delete", public_id=world.cera.public_id).status_code == expected


@pytest.mark.parametrize("role", [Role.BARBER, Role.VIEWER])
def test_quien_tiene_inventario_ver_lee_pero_no_edita(world, member, role):
    login = world.ana_login if role == Role.BARBER else member(role, world.shop)
    client = Client()
    client.force_login(login.user)

    assert client.get(reverse("api_products")).status_code == 200
    assert post(client, "api_product_edit", _new_product(), public_id=world.cera.public_id).status_code == 403


def test_crear_exige_csrf(world):
    client = Client(enforce_csrf_checks=True)
    logged = logged_in_with_mfa(world.owner.user)
    client.cookies = logged.cookies

    rejected = client.post(reverse("api_product_create"), _new_product(), content_type="application/json")
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(
        reverse("api_product_create"), _new_product(), content_type="application/json", HTTP_X_CSRFTOKEN=token
    )

    assert (rejected.status_code, set(rejected.json())) == (403, SHAPE)
    assert accepted.status_code == 201


def test_un_producto_que_no_existe_responde_404_con_la_forma_comun(world, owner_client):
    response = owner_client.get(reverse("api_product", kwargs={"public_id": uuid.uuid4()}))

    assert response.status_code == 404
    assert response.json() == {"detail": GENERIC_MESSAGES[404], "code": "not_found", "field_errors": {}}
