"""Fiados en la API: la cartera de la sede, el abono solo en la sede de origen y por `record_money`, nunca mayor
que la deuda ni dos veces, y la deuda nunca negativa aunque lleguen varios abonos a la vez."""

import threading

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse

from apps.cash.models import CashMovement, MovementKind
from apps.core.tenant_context import tenant_context
from apps.receivables.board import PAGE_SIZE
from apps.receivables.models import Receivable, ReceivablePayment, ReceivableStatus
from apps.receivables.services import STALE_BALANCE
from apps.tenancy.branch_scope import WRITE_NEEDS_ONE_BRANCH
from apps.tenancy.roles import Role
from tests.api.sales_support import choose_branch, credit, open_order, post
from tests.concurrency import run_threads

pytestmark = pytest.mark.django_db

SHAPE = {"detail", "code", "field_errors"}


def _as(member_fixture, world, role: Role) -> Client:
    client = Client()
    client.force_login(member_fixture(role, world.shop, email=f"{role}-fiados@a.test").user)
    return client


def _pay(client: Client, receivable: Receivable, amount: str, *, method: str = "efectivo", expected: str | None = None):
    body = {"amount": amount, "method": method, "expected_balance": expected or str(receivable.balance)}
    return post(client, "api_receivable_pay", body, public_id=receivable.public_id)


def _balance(receivable: Receivable):
    receivable.refresh_from_db()
    return receivable.balance


def test_la_lista_trae_la_cartera_y_las_pestanas_con_su_conteo(world, cashier_client):
    debt = credit(world, world.laura, total="40000")
    paid = credit(world, world.laura, total="10000")
    _pay(cashier_client, paid, "10000")

    pending = cashier_client.get(reverse("api_receivables")).json()
    settled = cashier_client.get(reverse("api_receivables"), {"pestana": "pagados"}).json()

    assert [row["id"] for row in pending["results"]] == [str(debt.public_id)]
    assert pending["portfolio"]["pending"] == {"total": "40000.00", "count": 1, "clients": 1}
    assert pending["portfolio"]["collected"] == {"total": "10000.00", "count": 1}
    assert {tab["value"]: tab["count"] for tab in pending["tabs"]} == {"pendientes": 1, "vencidos": 0, "pagados": 1}
    assert [(row["id"], row["due_text"]) for row in settled["results"]] == [(str(paid.public_id), "Pagado")]
    assert pending["page_size"] == PAGE_SIZE


def test_el_detalle_trae_su_comanda_y_sus_abonos(world, cashier_client):
    order = open_order(world, client=world.laura.public_id)
    parts = [{"method": "nequi", "amount": "15000"}, {"method": "fiado", "amount": "10000"}]
    post(cashier_client, "api_order_checkout", {"parts": parts}, public_id=order.public_id)
    debt = Receivable.objects.get()
    _pay(cashier_client, debt, "4000", method="nequi")

    detail = cashier_client.get(reverse("api_receivable", kwargs={"public_id": debt.public_id})).json()

    assert detail["order"] == {"id": str(order.public_id), "number": order.number}
    assert (detail["total"], detail["paid"], detail["balance"]) == ("10000.00", "4000.00", "6000.00")
    assert [(payment["method"], payment["amount"]) for payment in detail["payments"]] == [("Nequi", "4000.00")]
    assert detail["actions"] == {"pay": True}


def test_la_comanda_enlaza_el_fiado_que_genero_solo_a_quien_ve_fiados(world, cashier_client):
    order = open_order(world, client=world.laura.public_id)
    post(cashier_client, "api_order_checkout", {"parts": [{"method": "fiado"}]}, public_id=order.public_id)
    ana = Client()
    ana.force_login(world.ana_login.user)
    url = reverse("api_order", kwargs={"public_id": order.public_id})

    for_cashier, for_barber = cashier_client.get(url).json(), ana.get(url).json()

    assert for_cashier["receivable"] == {
        "id": str(Receivable.objects.get().public_id),
        "balance": "25000.00",
        "status": ReceivableStatus.PENDING,
    }
    assert for_barber["receivable"] is None


def test_un_abono_parcial_entra_a_la_caja_de_la_sede_y_uno_total_lo_deja_pagado(world, cashier_client):
    debt = credit(world, world.laura, total="25000")

    partial = _pay(cashier_client, debt, "10000", method="nequi")
    total = _pay(cashier_client, debt, "15000", expected="15000.00")

    assert partial.json()["balance"] == "15000.00"
    assert (total.json()["balance"], total.json()["status"]) == ("0.00", ReceivableStatus.PAID)
    movements = CashMovement.objects.filter(kind=MovementKind.RECEIVABLE_PAYMENT)
    assert {movement.session_id for movement in movements} == {world.session.pk}
    assert total.json()["actions"]["pay"] is False


def test_la_referencia_queda_en_el_abono_y_la_nota_en_su_movimiento_de_caja(world, cashier_client):
    """Como en el pago de una comanda: la referencia en el abono, ligado uno a uno a su movimiento de caja."""
    debt = credit(world, world.laura)
    body = {
        "amount": "5000",
        "method": "nequi",
        "reference": "Nequi 4821",
        "note": "Abonó al recoger a su hijo",
        "expected_balance": "25000.00",
    }

    response = post(cashier_client, "api_receivable_pay", body, public_id=debt.public_id)

    payment = ReceivablePayment.objects.select_related("cash_movement").get()
    assert payment.reference == "Nequi 4821"
    assert payment.cash_movement.kind == MovementKind.RECEIVABLE_PAYMENT
    assert payment.cash_movement.description == "Abono a fiado de Laura Gómez · Abonó al recoger a su hijo"
    assert response.json()["payments"][0]["reference"] == "Nequi 4821"


def test_una_referencia_o_una_nota_mas_largas_que_el_tope_se_rechazan(world, cashier_client):
    debt = credit(world, world.laura)
    body = {"amount": "5000", "method": "nequi", "expected_balance": "25000.00"}

    long_reference = post(
        cashier_client, "api_receivable_pay", {**body, "reference": "x" * 81}, public_id=debt.public_id
    )
    long_note = post(cashier_client, "api_receivable_pay", {**body, "note": "x" * 201}, public_id=debt.public_id)

    assert list(long_reference.json()["field_errors"]) == ["reference"]
    assert list(long_note.json()["field_errors"]) == ["note"]
    assert not ReceivablePayment.objects.exists()


def test_el_cajero_de_centro_no_ve_ni_abona_los_fiados_de_norte(world, norte, cashier_client):
    debt = credit(world, world.laura, branch=norte)

    listing = cashier_client.get(reverse("api_receivables")).json()
    detail = cashier_client.get(reverse("api_receivable", kwargs={"public_id": debt.public_id}))

    assert listing["results"] == []
    assert listing["portfolio"]["pending"]["total"] == "0.00"
    assert detail.status_code == 404
    assert _pay(cashier_client, debt, "1000").status_code == 404
    assert _balance(debt) == 25000


def test_abonar_fuera_de_la_sede_de_origen_se_rechaza(world, norte, owner_client):
    debt = credit(world, world.laura)  # nace en Centro

    choose_branch(owner_client, norte)
    from_norte = _pay(owner_client, debt, "1000")
    assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200
    from_all = _pay(owner_client, debt, "1000")
    detail = owner_client.get(reverse("api_receivable", kwargs={"public_id": debt.public_id})).json()

    assert from_norte.status_code == 404  # en otra sede el fiado no se encuentra, como uno de otra barbería
    assert (from_all.status_code, from_all.json()["detail"]) == (400, WRITE_NEEDS_ONE_BRANCH)
    assert (detail["actions"]["pay"], detail["needs_branch"], detail["branch"]) == (False, True, "Centro")
    assert _balance(debt) == 25000
    assert not ReceivablePayment.objects.exists()


def test_un_abono_mayor_que_la_deuda_se_rechaza(world, cashier_client):
    debt = credit(world, world.laura, total="20000")

    response = _pay(cashier_client, debt, "20001")

    assert (response.status_code, response.json()["code"]) == (400, "over_balance")
    assert set(response.json()) == SHAPE
    assert _balance(debt) == 20000


def test_un_segundo_envio_del_mismo_abono_se_rechaza(world, cashier_client):
    debt = credit(world, world.laura, total="20000")

    first = _pay(cashier_client, debt, "5000", expected="20000.00")
    second = _pay(cashier_client, debt, "5000", expected="20000.00")

    assert first.status_code == 200
    assert (second.status_code, second.json()["code"], second.json()["detail"]) == (400, "stale_balance", STALE_BALANCE)
    assert _balance(debt) == 15000


def test_una_forma_de_pago_no_habilitada_o_un_monto_float_se_rechazan(world, cashier_client):
    debt = credit(world, world.laura)

    unknown = _pay(cashier_client, debt, "1000", method="bitcoin")
    as_float = post(
        cashier_client,
        "api_receivable_pay",
        {"amount": 1000.5, "method": "efectivo", "expected_balance": "25000.00"},
        public_id=debt.public_id,
    )

    assert list(unknown.json()["field_errors"]) == ["method"]
    assert list(as_float.json()["field_errors"]) == ["amount"]
    assert _balance(debt) == 25000


def test_cada_rol_lee_y_abona_segun_roles_py(world, member):
    debt = credit(world, world.laura)
    viewer, barber = _as(member, world, Role.VIEWER), _as(member, world, Role.BARBER)

    assert viewer.get(reverse("api_receivables")).status_code == 200
    assert viewer.get(reverse("api_receivable", kwargs={"public_id": debt.public_id})).json()["actions"]["pay"] is False
    assert _pay(viewer, debt, "1000").status_code == 403
    assert barber.get(reverse("api_receivables")).status_code == 403
    assert _balance(debt) == 25000


def test_abonar_exige_csrf(world):
    debt = credit(world, world.laura)
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)
    body = {"amount": "1000", "method": "efectivo", "expected_balance": "25000.00"}
    url = reverse("api_receivable_pay", kwargs={"public_id": debt.public_id})

    rejected = client.post(url, body, content_type="application/json")
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)

    assert rejected.status_code == 403
    assert accepted.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_abonos_simultaneos_nunca_dejan_la_deuda_negativa(world):
    """Tres pestañas abonan 15 000 a una deuda de 25 000 a la vez: `add_payment` bloquea el fiado y solo pasa uno."""
    debt = credit(world, world.laura, total="25000")
    barrier = threading.Barrier(3)
    statuses: list[int] = []

    def pay() -> None:
        try:
            client = Client()
            client.force_login(world.cashier.user)
            barrier.wait()
            statuses.append(_pay(client, debt, "15000", expected="25000.00").status_code)
        finally:
            connection.close()

    run_threads([threading.Thread(target=pay, name=f"abono-{number}") for number in range(3)])

    assert sorted(statuses) == [200, 400, 400]
    with tenant_context(world.shop.pk):
        assert _balance(debt) == 10000
        assert ReceivablePayment.objects.count() == 1
