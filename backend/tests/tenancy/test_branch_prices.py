"""Fase S4a: precios por sede (decisión 17), barbero de la sede y "Mis cortes" por sede."""

from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.catalog import services as catalog
from apps.inventory import services as inventory
from apps.sales import services as sales
from apps.sales.models import OrderItem
from apps.sales.selectors import barber_performance, my_cuts_today
from apps.sales.services.open_orders import BARBER_OTHER_BRANCH
from apps.staff import services as staff
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

D = Decimal


def _order_with_cut(world, scope):
    order = sales.create_order(world.owner, scope, barber=world.ana.public_id)
    item = sales.add_item(world.owner, order.public_id, scope=scope, service=world.corte.public_id)
    return order, item


# ── Precio por sede ──────────────────────────────────────────────────────────


def test_la_comanda_toma_el_precio_de_su_sede_y_si_no_hay_el_del_catalogo(world, norte):
    catalog.set_service_branch_price(
        world.owner, world.corte.public_id, scope=scope_of(world.owner, norte), price=D("30000")
    )

    _, in_norte = _order_with_cut(world, scope_of(world.owner, norte))
    _, in_centro = _order_with_cut(world, scope_of(world.owner, world.branch))

    assert (in_norte.unit_price, in_centro.unit_price) == (D("30000"), D("25000"))


def test_el_cobro_rapido_usa_el_precio_de_la_sede_para_servicios_y_productos(world, norte):
    in_norte = scope_of(world.owner, norte)
    catalog.set_service_branch_price(world.owner, world.corte.public_id, scope=in_norte, price=D("30000"))
    inventory.set_product_branch_price(world.owner, world.cera.public_id, scope=in_norte, price=D("22000"))

    cut = sales.quick_register(
        world.owner, in_norte, barber=world.ana.public_id, method="efectivo", service=world.corte.public_id
    )
    wax = sales.quick_register(
        world.owner, in_norte, barber=world.ana.public_id, method="efectivo", product=world.cera.public_id
    )

    assert (cut.total, wax.total) == (D("30000"), D("22000"))


def test_el_precio_guardado_en_el_item_no_cambia_si_despues_cambia_el_de_la_sede(world, norte):
    in_norte = scope_of(world.owner, norte)
    catalog.set_service_branch_price(world.owner, world.corte.public_id, scope=in_norte, price=D("30000"))
    order, item = _order_with_cut(world, in_norte)

    catalog.set_service_branch_price(world.owner, world.corte.public_id, scope=in_norte, price=D("35000"))
    closed = sales.close_order(
        world.owner, order.public_id, scope=in_norte, payments=[{"method": "efectivo", "amount": D("30000")}]
    )

    assert OrderItem.objects.get(pk=item.pk).unit_price == D("30000") and closed.total == D("30000")


def test_quitar_el_precio_de_la_sede_vuelve_al_del_catalogo(world, norte):
    in_norte = scope_of(world.owner, norte)
    catalog.set_service_branch_price(world.owner, world.corte.public_id, scope=in_norte, price=D("30000"))
    catalog.remove_service_branch_price(world.owner, world.corte.public_id, scope=in_norte)

    assert _order_with_cut(world, in_norte)[1].unit_price == D("25000")
    actions = list(AuditLog.objects.filter(branch=norte).values_list("action", flat=True))
    assert actions.count("precio_sede.fijar") == 1 and actions.count("precio_sede.quitar") == 1


@pytest.mark.parametrize("role", [Role.CASHIER, Role.BARBER, Role.VIEWER])
def test_solo_dueno_y_administrador_cambian_precios(world, member, norte, role):
    other = member(role, world.shop, email=f"precio-{role}@a.test")
    with pytest.raises(PermissionDenied):
        catalog.set_service_branch_price(other, world.corte.public_id, scope=scope_of(other), price=D("1"))
    with pytest.raises(PermissionDenied):
        inventory.set_product_branch_price(other, world.cera.public_id, scope=scope_of(other), price=D("1"))


def test_el_administrador_fija_precios_y_queda_auditado(world, member, norte):
    admin = member(Role.ADMIN, world.shop)
    price = inventory.set_product_branch_price(
        admin, world.cera.public_id, scope=scope_of(admin, norte), price=D("21000")
    )

    event = AuditLog.objects.get(action="precio_sede.fijar", entity_id=str(price.public_id))
    assert (event.branch, event.after["price"], event.actor) == (norte, "21000.00", admin.user)


def test_un_precio_de_sede_no_es_negativo_ni_se_fija_en_todas(world, norte):
    with pytest.raises(ValidationError):
        catalog.set_service_branch_price(
            world.owner, world.corte.public_id, scope=scope_of(world.owner, norte), price=D("-1")
        )
    with pytest.raises(ValidationError):
        catalog.set_service_branch_price(
            world.owner, world.corte.public_id, scope=scope_of(world.owner, everything=True), price=D("1")
        )


# ── Barbero de la sede ───────────────────────────────────────────────────────


def test_un_barbero_de_otra_sede_no_se_elige_en_la_comanda(world, norte):
    only_centro = staff.create_barber(
        world.owner,
        {"display_name": "Carla"},
        commission_type="percentage",
        commission_value=40,
        branches=[world.branch.public_id],
    )
    in_norte = scope_of(world.owner, norte)

    with pytest.raises(ValidationError) as on_create:
        sales.create_order(world.owner, in_norte, barber=only_centro.public_id)
    order = sales.create_order(world.owner, in_norte)
    with pytest.raises(ValidationError) as on_item:
        sales.add_item(
            world.owner, order.public_id, scope=in_norte, service=world.corte.public_id, barber=only_centro.public_id
        )

    assert on_create.value.message_dict["barber"] == on_item.value.message_dict["barber"] == [BARBER_OTHER_BRANCH]


def test_un_barbero_inactivo_no_se_elige(world):
    staff.deactivate_barber(world.owner, world.ana.public_id)
    with pytest.raises(ValidationError) as error:
        sales.create_order(world.owner, scope_of(world.owner), barber=world.ana.public_id)
    assert "barber" in error.value.message_dict


# ── Mis cortes y rendimiento por sede ────────────────────────────────────────


def test_mis_cortes_de_hoy_y_el_rendimiento_van_por_la_sede(world, norte):
    sell(world, world.ana, service=world.corte)  # uno en Centro
    for _ in range(2):  # dos en Norte
        sales.quick_register(
            world.owner,
            scope_of(world.owner, norte),
            barber=world.ana.public_id,
            method="efectivo",
            service=world.corte.public_id,
        )
    ana = world.ana_login

    assert my_cuts_today(ana, scope=scope_of(ana, world.branch))["cuts_today"] == 1
    assert my_cuts_today(ana, scope=scope_of(ana, norte))["cuts_today"] == 2
    in_norte = barber_performance(world.owner, world.ana.public_id, scope=scope_of(world.owner, norte))
    everywhere = barber_performance(world.owner, world.ana.public_id, scope=scope_of(world.owner, everything=True))
    assert (in_norte["orders_count"], everywhere["orders_count"]) == (2, 3)
