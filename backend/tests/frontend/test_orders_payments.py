"""Pago combinado y cambio de cliente en Comandas (fase F3b)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clients import services as clients
from apps.core.tenant_context import tenant_context
from apps.receivables.models import Receivable
from apps.sales import services as sales
from apps.sales.models import Order, OrderStatus, Payment
from apps.staff.models import BarberBranch
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

D = Decimal
P = sales.PaymentPart


def _order(world, *, client=None) -> Order:
    """Un corte de 25 000 en Centro, abierto."""
    scope = scope_of(world.cashier, world.branch)
    order = sales.create_order(world.cashier, scope, client=client, barber=world.ana.public_id)
    sales.add_item(world.cashier, order.public_id, scope=scope, service=world.corte.public_id)
    return order


def _pay(world, order, *parts, received=None):
    plan = sales.Checkout(parts=parts, received=received)
    return sales.checkout_order(world.cashier, order.public_id, scope=scope_of(world.cashier), checkout=plan)


def _client(membership) -> Client:
    client = Client()
    client.force_login(membership.user)
    return client


# ── Pago combinado ───────────────────────────────────────────────────────────


def test_una_suma_distinta_del_total_se_rechaza(world):
    order = _order(world)
    with pytest.raises(ValidationError, match="exactamente el total"):
        _pay(world, order, P("efectivo", D("10000")), P("nequi", D("10000")), received=D("10000"))
    order.refresh_from_db()
    assert order.status == OrderStatus.OPEN


def test_efectivo_y_nequi_con_vueltas_solo_sobre_el_efectivo(world):
    order = _order(world)

    closed, change = _pay(world, order, P("efectivo", D("15000")), P("nequi", D("10000"), "N-77"), received=D("20000"))

    assert change == D("5000")  # 20 000 recibidos menos los 15 000 en efectivo
    paid = dict(Payment.objects.filter(order=closed).values_list("method", "amount"))
    assert paid == {"efectivo": D("15000"), "nequi": D("10000")}


def test_el_doble_envio_del_pago_dividido_no_duplica(world):
    order = _order(world)
    data = {"metodo": "efectivo", "recibido": "15000"}
    data |= {
        "parte_1_metodo": "efectivo",
        "parte_1_monto": "15000",
        "parte_2_metodo": "nequi",
        "parte_2_monto": "10000",
    }
    cashier = _client(world.cashier)

    cashier.post(reverse("orders_checkout", args=[order.public_id]), data)
    cashier.post(reverse("orders_checkout", args=[order.public_id]), data)

    assert Payment.objects.filter(order=order).count() == 2


def test_el_fiado_combinado_exige_cliente(world):
    walk_in = _order(world)
    with pytest.raises(ValidationError, match="cliente"):
        _pay(world, walk_in, P("efectivo", D("10000")), P("fiado", D("15000")), received=D("10000"))

    with_client = _order(world, client=world.laura.public_id)
    closed, _ = _pay(world, with_client, P("efectivo", D("10000")), P("fiado", D("15000")), received=D("10000"))

    assert closed.amount_paid == D("10000")
    assert Receivable.objects.get(order=closed).total == D("15000")


# ── Cambiar cliente ──────────────────────────────────────────────────────────


def _change(world, order, client, membership=None):
    membership = membership or world.cashier
    return sales.change_order_client(membership, order.public_id, scope=scope_of(membership), client=client)


def test_cambiar_el_cliente_queda_en_la_auditoria_y_se_puede_quitar(world):
    order = _order(world)

    _change(world, order, world.laura.public_id)
    _change(world, order, None)

    order.refresh_from_db()
    assert order.client is None
    first, second = AuditLog.objects.filter(action="comanda.cambiar_cliente").order_by("pk")
    assert (first.before["client"], first.after["client"]) == (None, str(world.laura.public_id))
    assert (second.before["client"], second.after["client"]) == (str(world.laura.public_id), None)


def test_no_se_cambia_el_cliente_de_una_comanda_cerrada_o_anulada(world):
    closed = _order(world)
    _pay(world, closed, P("nequi"))
    cancelled = _order(world)
    sales.cancel_order(world.cashier, cancelled.public_id, scope=scope_of(world.cashier), reason="Error")

    for order in (closed, cancelled):
        with pytest.raises(ValidationError, match="no se puede modificar"):
            _change(world, order, world.laura.public_id)


def test_no_acepta_un_cliente_de_otra_barberia_ni_una_comanda_de_otra_sede(world, make_shop, member):
    other = make_shop("b")
    with tenant_context(other.pk):
        foreign = clients.create_client(
            member(Role.OWNER, other), {"full_name": "Ajeno"}, data_consent_at=timezone.now(), data_policy_version="1"
        )
    with pytest.raises(ValidationError, match="no existe"):
        _change(world, _order(world), foreign.public_id)

    norte = Branch.objects.create(name="Norte")
    BarberBranch.objects.create(barber=world.ana, branch=norte)
    in_norte = sales.create_order(world.owner, scope_of(world.owner, norte))
    url = reverse("orders_change_client", args=[in_norte.public_id])
    assert _client(world.cashier).post(url, {"cliente": str(world.laura.public_id)}).status_code == 404


def test_cambiar_el_cliente_exige_permiso(world, member, in_shop):
    viewer = member(Role.VIEWER, in_shop)  # ve comandas, pero no las edita
    order = _order(world)
    url = reverse("orders_change_client", args=[order.public_id])
    assert _client(viewer).post(url, {"cliente": str(world.laura.public_id)}).status_code == 403


# Sesión, alcance, marco, la lista, la comanda con su catálogo y el aviso de la caja, y una sola consulta
# para el buscador de clientes, sea cual sea el número de resultados.
DETAIL_WITH_SEARCH_QUERIES = 27


@pytest.mark.parametrize("matches", [1, 8])
def test_el_buscador_de_clientes_no_crece_con_los_resultados(world, django_assert_num_queries, matches):
    for number in range(matches):
        clients.create_client(
            world.owner, {"full_name": f"Cliente {number}"}, data_consent_at=timezone.now(), data_policy_version="1"
        )
    order = _order(world)
    cashier = _client(world.cashier)
    url = reverse("orders_detail", args=[order.public_id])

    with django_assert_num_queries(DETAIL_WITH_SEARCH_QUERIES):
        response = cashier.get(url, {"buscar_cliente": "Cliente"})

    assert len(response.context["client_search"]["results"]) == matches
