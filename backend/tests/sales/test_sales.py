import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.utils import timezone

from apps.cash import selectors as cash_selectors
from apps.cash import services as cash
from apps.cash.models import CashMovement, MovementKind
from apps.catalog import services as catalog
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.receivables import services as receivables
from apps.receivables.models import Receivable, ReceivableStatus
from apps.sales import selectors, services
from apps.sales.models import Order, OrderStatus, Payment, PaymentStatus
from apps.staff import services as staff
from apps.tenancy.models import BarbershopSettings, Branch
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db

D = Decimal


def _order(w, actor=None, **kwargs):
    actor = actor or w.cashier
    kwargs.setdefault("barber", w.ana.public_id)
    return services.create_order(actor, w.branch.public_id, **kwargs)


def _sold_corte(w, actor=None, **kwargs):
    order = _order(w, actor, **kwargs)
    services.add_item(actor or w.cashier, order.public_id, service=w.corte.public_id)
    return order


def _cash(amount):
    return [{"method": "efectivo", "amount": amount}]


def _error_code(excinfo) -> str:
    return excinfo.value.error_list[0].code


def _stocks(w):
    w.cera.refresh_from_db()
    w.cuchilla.refresh_from_db()
    return w.cera.current_stock, w.cuchilla.current_stock


# ── Comanda abierta ──────────────────────────────────────────────────────────


def test_el_numero_es_consecutivo_por_barberia(world, member, other_shop):
    first, second = _order(world), _order(world)
    assert (first.number, second.number) == (1, 2)
    with tenant_context(other_shop.pk):
        other_owner = member(Role.OWNER, other_shop)
        other = services.create_order(other_owner, Branch.objects.create(name="Otra").public_id)
    assert other.number == 1
    assert BarbershopSettings.objects.get().next_order_number == 3


def test_el_precio_sale_siempre_del_catalogo(world):
    order = _order(world)
    with pytest.raises(TypeError):
        services.add_item(world.cashier, order.public_id, service=world.corte.public_id, unit_price=D("1"))
    line = services.add_item(world.cashier, order.public_id, service=world.corte.public_id, quantity=2)
    assert (line.unit_price, line.line_total) == (D("25000"), D("50000"))

    catalog.update_service(world.owner, world.corte.public_id, price=D("99000"))
    line.refresh_from_db()
    assert line.unit_price == D("25000")  # queda el precio con que se agregó


def test_no_se_venden_servicios_ni_productos_inactivos_o_borrados(world):
    order = _order(world)
    catalog.deactivate_service(world.owner, world.barba.public_id)
    inventory.soft_delete_product(world.owner, world.cera.public_id)
    with pytest.raises(ValidationError):
        services.add_item(world.cashier, order.public_id, service=world.barba.public_id)
    with pytest.raises(ValidationError):
        services.add_item(world.cashier, order.public_id, product=world.cera.public_id)
    with pytest.raises(ValidationError):
        services.add_item(world.cashier, order.public_id, service=world.corte.public_id, product=world.cera.public_id)


def test_cambiar_cantidad_y_quitar_lineas_recalculan(world):
    order = _order(world)
    line = services.add_item(world.cashier, order.public_id, service=world.corte.public_id)
    services.add_item(world.cashier, order.public_id, product=world.cera.public_id)
    services.update_item_quantity(world.cashier, order.public_id, line.public_id, 3)
    order.refresh_from_db()
    assert order.subtotal == D("95000")
    services.remove_item(world.cashier, order.public_id, line.public_id)
    order.refresh_from_db()
    assert (order.subtotal, order.total) == (D("20000"), D("20000"))


def test_descuento_con_motivo_y_dentro_del_subtotal(world):
    order = _sold_corte(world)
    with pytest.raises(ValidationError):
        services.set_discount(world.cashier, order.public_id, D("1000"))
    with pytest.raises(ValidationError):
        services.set_discount(world.cashier, order.public_id, D("25001"), "Mucho")
    services.set_discount(world.cashier, order.public_id, D("1000"), "Promoción")
    order.refresh_from_db()
    assert (order.total, order.discount_reason) == (D("24000"), "Promoción")


def test_quitar_una_linea_no_puede_dejar_el_descuento_por_encima(world):
    order = _order(world)
    line = services.add_item(world.cashier, order.public_id, service=world.corte.public_id)
    services.add_item(world.cashier, order.public_id, service=world.barba.public_id)
    services.set_discount(world.cashier, order.public_id, D("20000"), "Promoción")
    with pytest.raises(ValidationError):
        services.remove_item(world.cashier, order.public_id, line.public_id)


def test_el_barbero_no_puede_descontar(world):
    order = _sold_corte(world, world.ana_login)
    with pytest.raises(PermissionDenied):
        services.set_discount(world.ana_login, order.public_id, D("1000"), "Amigo")


def test_cortesia_es_un_descuento_total_y_cierra_sin_pagos(world):
    order = _sold_corte(world)
    services.set_discount(world.cashier, order.public_id, D("25000"), "Cortesía por reclamo")
    closed = services.close_order(world.cashier, order.public_id)
    assert (closed.total, closed.payment_status, closed.commission_total) == (D("0"), PaymentStatus.PAID, D("0"))
    assert not CashMovement.objects.exists()


def test_espera_solo_entre_abierta_y_en_espera(world):
    order = _sold_corte(world)
    with pytest.raises(ValidationError):
        services.resume_order(world.cashier, order.public_id)
    services.hold_order(world.cashier, order.public_id)
    with pytest.raises(ValidationError):
        services.hold_order(world.cashier, order.public_id)
    services.resume_order(world.cashier, order.public_id)

    services.close_order(world.cashier, order.public_id, _cash("25000"))
    with pytest.raises(ValidationError) as excinfo:
        services.hold_order(world.cashier, order.public_id)
    assert _error_code(excinfo) == "not_editable"
    with pytest.raises(ValidationError):
        services.add_item(world.cashier, order.public_id, product=world.cera.public_id)


# ── Cierre ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("setup", "payments", "kwargs", "code"),
    [
        ("nada", _cash("25001"), {}, "overpaid"),
        ("nada", _cash("10000"), {}, "unpaid_balance"),
        ("sin_cliente", _cash("10000"), {"as_credit": True}, "credit_without_client"),
        ("caja_cerrada", _cash("25000"), {}, "no_open_session"),
    ],
    ids=["pago_mayor_al_total", "saldo_sin_fiado", "fiado_sin_cliente", "sin_caja_abierta"],
)
def test_cierres_rechazados_no_dejan_rastro(world, setup, payments, kwargs, code):
    if setup == "caja_cerrada":
        cash.close_session(world.cashier, world.session.public_id, D("50000"))
    client = None if setup == "sin_cliente" else world.laura.public_id
    order = _sold_corte(world, client=client)

    with pytest.raises(ValidationError) as excinfo:
        services.close_order(world.cashier, order.public_id, payments, **kwargs)

    assert _error_code(excinfo) == code
    order.refresh_from_db()
    assert order.status == OrderStatus.OPEN
    assert _stocks(world) == (5, 10)
    assert not Payment.objects.exists()
    assert not Receivable.objects.exists()


def test_metodo_no_habilitado_rechazado(world):
    settings = BarbershopSettings.objects.get()
    settings.enabled_payment_methods = ["efectivo"]
    settings.save()
    order = _sold_corte(world)
    with pytest.raises(ValidationError):
        services.close_order(world.cashier, order.public_id, [{"method": "nequi", "amount": "25000"}])
    assert _stocks(world) == (5, 10)


def test_servicio_sin_barbero_activo_no_se_cierra(world):
    order = services.create_order(world.cashier, world.branch.public_id)
    services.add_item(world.cashier, order.public_id, service=world.barba.public_id)
    with pytest.raises(ValidationError) as excinfo:
        services.close_order(world.cashier, order.public_id, _cash("15000"))
    assert _error_code(excinfo) == "missing_barber"

    other = _order(world, barber=world.beto.public_id)
    services.add_item(world.cashier, other.public_id, service=world.barba.public_id)
    staff.deactivate_barber(world.owner, world.beto.public_id)
    with pytest.raises(ValidationError):
        services.close_order(world.cashier, other.public_id, _cash("15000"))


def test_stock_insuficiente_al_cerrar_revierte_todo(world):
    order = _order(world)
    services.add_item(world.cashier, order.public_id, service=world.corte.public_id)
    services.add_item(world.cashier, order.public_id, product=world.cera.public_id, quantity=6)
    with pytest.raises(ValidationError) as excinfo:
        services.close_order(world.cashier, order.public_id, _cash("145000"))
    assert _error_code(excinfo) == "insufficient_stock"
    assert _stocks(world) == (5, 10)
    assert not CashMovement.objects.exists()


def test_fiado_con_cliente_crea_la_cuenta_por_cobrar(world):
    order = _sold_corte(world, client=world.laura.public_id)
    closed = services.close_order(world.cashier, order.public_id, _cash("10000"), as_credit=True)
    assert closed.payment_status == PaymentStatus.CREDIT
    debt = Receivable.objects.get(order=closed)
    assert (debt.client, debt.total, debt.balance, debt.status) == (
        world.laura,
        D("15000"),
        D("15000"),
        ReceivableStatus.PENDING,
    )


def test_fiado_sin_pagos_no_necesita_caja(world):
    cash.close_session(world.cashier, world.session.public_id, D("50000"))
    order = _sold_corte(world, client=world.laura.public_id)
    assert services.close_order(world.cashier, order.public_id, as_credit=True).payment_status == PaymentStatus.CREDIT


def test_el_limite_de_credito_cuenta_la_deuda_total_del_cliente(world):
    settings = BarbershopSettings.objects.get()
    settings.max_credit_per_client = D("20000")
    settings.save()
    receivables.create_manual(world.cashier, world.laura.public_id, D("8000"))
    order = _sold_corte(world, client=world.laura.public_id)
    with pytest.raises(ValidationError) as excinfo:
        services.close_order(world.cashier, order.public_id, _cash("10000"), as_credit=True)
    assert _error_code(excinfo) == "credit_limit"
    assert services.close_order(world.cashier, order.public_id, _cash("13000"), as_credit=True).pk


@pytest.mark.django_db(transaction=True)
def test_dos_cierres_simultaneos_cierran_una_sola_vez(world):
    """Defecto 10: el segundo espera el bloqueo y encuentra la comanda ya cerrada."""
    order = _sold_corte(world)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def close() -> None:
        try:
            with tenant_context(world.shop.pk):
                barrier.wait()
                services.close_order(world.cashier, order.public_id, _cash("25000"))
            outcomes.append("cerrada")
        except ValidationError as error:
            outcomes.append(error.error_list[0].code)
        finally:
            connection.close()

    threads = [threading.Thread(target=close) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["cerrada", "not_editable"]
    with tenant_context(world.shop.pk):
        assert Payment.objects.count() == 1
        assert CashMovement.objects.filter(kind=MovementKind.SALE).count() == 1
        assert _stocks(world) == (5, 9)


def test_registro_rapido_cobra_completo_en_un_paso(world):
    order = services.quick_register(
        world.cashier, world.branch.public_id, world.ana.public_id, "nequi", service=world.corte.public_id
    )
    assert (order.status, order.payment_status, order.amount_paid) == (
        OrderStatus.CLOSED,
        PaymentStatus.PAID,
        D("25000"),
    )
    product_sale = services.quick_register(
        world.cashier, world.branch.public_id, world.ana.public_id, "efectivo", product=world.cera.public_id
    )
    assert product_sale.total == D("20000")
    assert _stocks(world) == (4, 9)


# ── Anulación (defecto 12) ───────────────────────────────────────────────────


def _closed_full_order(w, **close_kwargs):
    order = _order(w, client=w.laura.public_id)
    services.add_item(w.cashier, order.public_id, service=w.corte.public_id)
    services.add_item(w.cashier, order.public_id, product=w.cera.public_id)
    payments = close_kwargs.pop(
        "payments", [{"method": "efectivo", "amount": "30000"}, {"method": "nequi", "amount": "15000"}]
    )
    return services.close_order(w.cashier, order.public_id, payments, **close_kwargs)


def test_anular_una_cerrada_restituye_stock_y_devuelve_pagos(world):
    order = _closed_full_order(world)
    assert _stocks(world) == (4, 9)

    cancelled = services.cancel_order(world.owner, order.public_id, "Cobro equivocado")

    assert (cancelled.status, cancelled.cancel_reason) == (OrderStatus.CANCELLED, "Cobro equivocado")
    assert _stocks(world) == (5, 10)
    refunds = CashMovement.objects.filter(kind=MovementKind.REFUND).order_by("pk")
    assert [(r.payment_method, r.amount, r.direction) for r in refunds] == [
        ("efectivo", D("30000"), "out"),
        ("nequi", D("15000"), "out"),
    ]
    assert cash_selectors.session_summary(world.cashier, world.session.public_id)["expected_cash"] == D("50000")


def test_anular_una_cerrada_anula_su_fiado_sin_abonos(world):
    order = _closed_full_order(world, payments=_cash("5000"), as_credit=True)
    services.cancel_order(world.owner, order.public_id, "Error")
    debt = Receivable.objects.get(order=order)
    assert (debt.status, debt.balance) == (ReceivableStatus.CANCELLED, D("0"))


def test_no_se_anula_una_comanda_cuyo_fiado_tiene_abonos(world):
    order = _closed_full_order(world, payments=_cash("5000"), as_credit=True)
    debt = Receivable.objects.get(order=order)
    receivables.add_payment(world.cashier, debt.public_id, D("1000"), "efectivo", world.branch.public_id)
    with pytest.raises(ValidationError) as excinfo:
        services.cancel_order(world.owner, order.public_id, "Error")
    assert _error_code(excinfo) == "has_payments"
    order.refresh_from_db()
    assert order.status == OrderStatus.CLOSED
    assert _stocks(world) == (4, 9)


def test_anular_una_cerrada_exige_caja_abierta_y_permiso(world):
    order = _closed_full_order(world)
    with pytest.raises(PermissionDenied):
        services.cancel_order(world.cashier, order.public_id, "Sin permiso")
    cash.close_session(world.cashier, world.session.public_id, D("80000"))
    with pytest.raises(ValidationError) as excinfo:
        services.cancel_order(world.owner, order.public_id, "Sin caja")
    assert _error_code(excinfo) == "no_open_session"


def test_anular_una_abierta_no_tiene_efectos_y_el_barbero_puede_con_la_suya(world):
    order = _sold_corte(world, world.ana_login)
    cancelled = services.cancel_order(world.ana_login, order.public_id, "El cliente se fue")
    assert cancelled.status == OrderStatus.CANCELLED
    assert _stocks(world) == (5, 10)
    with pytest.raises(ValidationError):
        services.cancel_order(world.owner, order.public_id, "Otra vez")
    with pytest.raises(ValidationError):
        services.cancel_order(world.owner, _order(world).public_id, "   ")


# ── Alcance del Barbero (defecto 6) ──────────────────────────────────────────


def test_el_barbero_ve_y_opera_solo_sus_comandas(world):
    mine = _sold_corte(world, barber=world.ana.public_id)
    created_by_me = services.create_order(world.ana_login, world.branch.public_id, barber=world.beto.public_id)
    theirs = _sold_corte(world, barber=world.beto.public_id)

    visible = {order.number for order in selectors.list_orders(world.ana_login)}
    assert visible == {mine.number, created_by_me.number}
    assert selectors.get_order(world.ana_login, mine.public_id) == mine
    with pytest.raises(Order.DoesNotExist):
        selectors.get_order(world.ana_login, theirs.public_id)
    with pytest.raises(Order.DoesNotExist):
        services.close_order(world.ana_login, theirs.public_id, _cash("25000"))
    assert {order.number for order in selectors.list_orders(world.cashier)} == {
        mine.number,
        created_by_me.number,
        theirs.number,
    }


def test_el_barbero_que_crea_queda_como_principal(world):
    order = services.create_order(world.ana_login, world.branch.public_id)
    assert order.barber == world.ana


def test_lista_paginada_y_filtrada(world):
    for _ in range(3):
        _order(world)
    closed = _sold_corte(world, barber=world.beto.public_id)
    services.close_order(world.cashier, closed.public_id, _cash("25000"))

    page = selectors.list_orders(world.cashier, page_size=2)
    assert (page.paginator.count, len(page.object_list), page.has_next()) == (4, 2, True)
    assert [o.number for o in selectors.list_orders(world.cashier, status=OrderStatus.CLOSED)] == [closed.number]
    assert [o.number for o in selectors.list_orders(world.cashier, barber=world.beto.public_id)] == [closed.number]


def test_nombres_marcados_si_se_borro_lo_vendido(world):
    order = _closed_full_order(world)
    inventory.soft_delete_product(world.owner, world.cera.public_id)
    staff.update_barber(world.owner, world.beto.public_id, {"membership": None})
    staff.soft_delete_barber(world.owner, world.beto.public_id)
    world.beto.refresh_from_db()

    detail = selectors.get_order(world.owner, order.public_id)
    names = sorted(selectors.item_display_name(item) for item in detail.items.all())
    assert names == ["Cera (eliminado)", "Corte"]
    assert selectors.barber_display_name(world.beto) == "Beto (eliminado)"


# ── Rendimiento y "mis cortes" (reglas 44 y 54) ──────────────────────────────


def test_rendimiento_lo_ve_quien_tiene_permiso_y_cada_barbero_el_suyo(world, member):
    order = _sold_corte(world)
    services.close_order(world.cashier, order.public_id, _cash("25000"))

    assert selectors.barber_performance(world.ana_login, world.ana.public_id)["commission_total"] == D("10000.00")
    with pytest.raises(PermissionDenied):
        selectors.barber_performance(world.beto_login, world.ana.public_id)
    viewer = member(Role.VIEWER, world.shop)
    assert selectors.barber_performance(viewer, world.ana.public_id)["services_count"] == 1


def test_rendimiento_por_defecto_son_30_dias_contando_hoy(world):
    inside, outside = (_sold_corte(world) for _ in range(2))
    for order in (inside, outside):
        services.close_order(world.cashier, order.public_id, _cash("25000"))
    today = selectors.local_today(world.owner)
    Order.objects.filter(pk=inside.pk).update(closed_at=timezone.now() - timedelta(days=29))
    Order.objects.filter(pk=outside.pk).update(closed_at=timezone.now() - timedelta(days=30, hours=1))

    performance = selectors.barber_performance(world.owner, world.ana.public_id)

    assert (performance["date_from"], performance["date_to"]) == (today - timedelta(days=29), today)
    assert performance["orders_count"] == 1


def test_mis_cortes_cuenta_servicios_sin_dinero(world):
    order = _order(world)
    services.add_item(world.cashier, order.public_id, service=world.corte.public_id, quantity=2)
    services.add_item(world.cashier, order.public_id, product=world.cera.public_id)
    services.close_order(world.cashier, order.public_id, _cash("70000"))
    assert selectors.my_cuts_today(world.ana_login) == {"cuts_today": 2}
    assert selectors.my_cuts_today(world.beto_login) == {"cuts_today": 0}
    assert selectors.my_cuts_today(world.cashier) == {"cuts_today": 0}


# ── Aislamiento ──────────────────────────────────────────────────────────────


def test_otra_barberia_no_ve_ni_toca_comandas_ajenas(world, member, other_shop):
    order = _sold_corte(world)
    with tenant_context(other_shop.pk):
        outsider = member(Role.OWNER, other_shop)
        assert selectors.list_orders(outsider).paginator.count == 0
        with pytest.raises(Order.DoesNotExist):
            selectors.get_order(outsider, order.public_id)
        with pytest.raises(Order.DoesNotExist):
            services.cancel_order(outsider, order.public_id, "Ajena")
