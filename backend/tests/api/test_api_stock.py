"""Entradas, ajustes y traslados en la API (reglas 33 y 34, decisión 6): siempre en la sede del alcance, nunca dejan
el stock negativo, el motivo es obligatorio, el traslado solo va a otra sede activa de la barbería y una llave mueve
el stock una sola vez aunque lleguen dos envíos a la vez."""

import threading
import uuid
from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse

from apps.api.exceptions import GENERIC_MESSAGES
from apps.core.tenant_context import tenant_context
from apps.inventory.models import MovementType, StockMovement
from apps.tenancy import services as tenancy
from apps.tenancy.branch_scope import WRITE_NEEDS_ONE_BRANCH
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role
from tests.api.inventory_support import entry, move
from tests.api.sales_support import choose_branch, post
from tests.concurrency import run_threads
from tests.conftest import stock_of
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db

MISSING_REASON = {"reason": ["El motivo es obligatorio."]}
BAD_DESTINATION = {"destination": ["La sede de destino no existe o está inactiva."]}


def _adjust(client: Client, product, quantity: int, reason: str = "Conteo", **body):
    return move(client, "api_product_adjustment", product, quantity=quantity, reason=reason, **body)


def _transfer(client: Client, product, destination: Branch, quantity: int = 2, **body):
    body = {"destination": str(destination.public_id), "quantity": quantity, "reason": "Reparto", **body}
    return move(client, "api_product_transfer", product, **body)


# ── Entrada y ajuste ─────────────────────────────────────────────────────────


def test_la_entrada_suma_en_la_sede_con_su_costo_y_motivo(world, owner_client):
    response = entry(owner_client, world.cera, quantity=3, unit_cost="7500", reason="Compra a proveedor")

    assert (response.status_code, response.json()["stock"]) == (201, 8)
    movement = StockMovement.objects.filter(product=world.cera).latest("created_at")
    assert (movement.movement_type, movement.branch, movement.unit_cost, movement.reason) == (
        MovementType.ENTRY,
        world.branch,
        Decimal("7500"),
        "Compra a proveedor",
    )


def test_el_ajuste_resta_con_signo(world, owner_client):
    response = _adjust(owner_client, world.cera, -2)

    assert (response.status_code, response.json()["stock"]) == (201, 3)


def test_un_ajuste_sin_motivo_se_rechaza(world, owner_client):
    response = _adjust(owner_client, world.cera, -1, reason="   ")

    assert (response.status_code, response.json()["field_errors"]) == (400, MISSING_REASON)
    assert stock_of(world.cera, world.branch) == 5


def test_el_stock_nunca_queda_negativo(world, norte, owner_client):
    choose_branch(owner_client, world.branch)

    adjusted = _adjust(owner_client, world.cera, -6)
    moved = _transfer(owner_client, world.cera, norte, quantity=6)

    assert (adjusted.status_code, moved.status_code) == (400, 400)
    assert adjusted.json()["code"] == "insufficient_stock"
    assert "Stock insuficiente de Cera en Centro" in adjusted.json()["detail"]
    assert (stock_of(world.cera, world.branch), stock_of(world.cera, norte)) == (5, 3)


# ── Llave del intento ────────────────────────────────────────────────────────


def test_un_reenvio_de_la_entrada_con_la_misma_llave_mueve_el_stock_una_sola_vez(world, owner_client):
    key = str(uuid.uuid4())

    first = entry(owner_client, world.cera, quantity=3, request_key=key)
    again = entry(owner_client, world.cera, quantity=3, request_key=key)

    assert (first.status_code, again.status_code) == (201, 200)
    assert (again.json()["stock"], stock_of(world.cera, world.branch)) == (8, 8)
    assert StockMovement.objects.filter(request_key=key).count() == 1


def test_la_misma_llave_con_otros_datos_responde_409_sin_mover_nada(world, norte, owner_client):
    choose_branch(owner_client, world.branch)
    key = str(uuid.uuid4())
    entry(owner_client, world.cera, quantity=3, request_key=key)

    conflicts = [
        entry(owner_client, world.cera, quantity=4, request_key=key),
        entry(owner_client, world.cuchilla, quantity=3, request_key=key),
        _adjust(owner_client, world.cera, 3, request_key=key),
        _transfer(owner_client, world.cera, norte, request_key=key),
    ]

    assert [response.status_code for response in conflicts] == [409, 409, 409, 409]
    assert conflicts[0].json() == {"detail": GENERIC_MESSAGES[409], "code": "conflict", "field_errors": {}}
    assert (stock_of(world.cera, world.branch), stock_of(world.cuchilla, world.branch)) == (8, 10)


def test_un_reenvio_del_traslado_devuelve_el_mismo_sin_mover_otra_vez(world, norte, owner_client):
    choose_branch(owner_client, world.branch)
    key = str(uuid.uuid4())

    first = _transfer(owner_client, world.cera, norte, request_key=key)
    again = _transfer(owner_client, world.cera, norte, request_key=key)
    elsewhere = _transfer(owner_client, world.cera, world.branch, request_key=key)

    assert (first.status_code, again.status_code, elsewhere.status_code) == (201, 200, 409)
    assert (stock_of(world.cera, world.branch), stock_of(world.cera, norte)) == (3, 5)


@pytest.mark.django_db(transaction=True)
def test_dos_envios_simultaneos_de_la_misma_entrada_la_registran_una_vez(world, owner_client):
    """Doble clic o un reintento de red: la restricción única de la llave deja pasar uno; el otro recibe lo hecho."""
    key = str(uuid.uuid4())
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def send() -> None:
        try:
            client = Client()
            client.force_login(world.owner.user)
            barrier.wait()
            statuses.append(entry(client, world.cera, quantity=3, request_key=key).status_code)
        finally:
            connection.close()

    run_threads([threading.Thread(target=send, name=f"entrada-{number}") for number in range(2)])

    assert sorted(statuses) == [200, 201]
    with tenant_context(world.shop.pk):
        assert stock_of(world.cera, world.branch) == 8
        assert StockMovement.objects.filter(request_key=key).count() == 1


# ── Traslados ────────────────────────────────────────────────────────────────


def test_el_traslado_sale_de_la_sede_y_entra_en_la_otra_con_el_mismo_traslado(world, norte, owner_client):
    choose_branch(owner_client, world.branch)

    response = _transfer(owner_client, world.cera, norte, quantity=2)

    assert response.status_code == 201
    assert response.json()["destinations"] == [{"id": str(norte.public_id), "name": "Norte", "stock": 5}]
    out, into = StockMovement.objects.filter(transfer_id__isnull=False).order_by("pk")
    assert (out.branch, out.quantity, into.branch, into.quantity) == (world.branch, -2, norte, 2)
    assert out.transfer_id == into.transfer_id


def test_no_se_traslada_a_una_sede_inactiva_de_otra_barberia_ni_a_la_misma(world, norte, owner_client, other_shop):
    sur = tenancy.create_branch(world.owner, {"name": "Sur"})
    tenancy.deactivate_branch(world.owner, sur.public_id)
    with tenant_context(other_shop.pk):
        foreign = Branch.objects.get()
    choose_branch(owner_client, world.branch)

    responses = [_transfer(owner_client, world.cera, branch) for branch in (sur, foreign)]
    same = _transfer(owner_client, world.cera, world.branch)

    assert [(r.status_code, r.json()["field_errors"]) for r in responses] == [(400, BAD_DESTINATION)] * 2
    assert same.json()["field_errors"] == {
        "destination": ["El traslado necesita una sede de destino distinta a la de origen."]
    }
    assert stock_of(world.cera, world.branch) == 5


@pytest.mark.django_db(transaction=True)
def test_traslados_cruzados_a_la_vez_conservan_el_total_entre_sedes(world, norte, owner_client):
    """Dos de Centro a Norte y dos de Norte a Centro al mismo tiempo: ningún bloqueo cruzado y el total no cambia."""
    plan = [(world.branch, norte, 2), (world.branch, norte, 2), (norte, world.branch, 1), (norte, world.branch, 1)]
    barrier = threading.Barrier(len(plan))
    statuses: list[int] = []

    def send(origin: Branch, destination: Branch, quantity: int) -> None:
        try:
            client = Client()
            client.force_login(world.owner.user)
            choose_branch(client, origin)
            barrier.wait()
            statuses.append(_transfer(client, world.cera, destination, quantity=quantity).status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=send, args=step, name=f"traslado-{n}") for n, step in enumerate(plan)]
    run_threads(threads)

    assert statuses == [201] * len(plan)
    with tenant_context(world.shop.pk):
        assert (stock_of(world.cera, world.branch), stock_of(world.cera, norte)) == (3, 5)
        assert stock_of(world.cera) == 8


# ── Alcance, permisos y CSRF ─────────────────────────────────────────────────


def test_en_todas_no_se_mueve_stock(world, norte, owner_client):
    assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200

    responses = [
        entry(owner_client, world.cera),
        _adjust(owner_client, world.cera, 1),
        _transfer(owner_client, world.cera, norte),
    ]

    assert [(r.status_code, r.json()["detail"]) for r in responses] == [(400, WRITE_NEEDS_ONE_BRANCH)] * 3
    assert stock_of(world.cera) == 8


@pytest.mark.parametrize(
    ("role", "expected"), [(Role.CASHIER, 403), (Role.BARBER, 403), (Role.VIEWER, 403), (Role.ADMIN, 201)]
)
def test_mueve_stock_quien_tiene_inventario_ajustar(world, member, role, expected):
    login = {Role.CASHIER: world.cashier, Role.BARBER: world.ana_login}.get(role) or member(role, world.shop)
    client = logged_in_with_mfa(login.user)

    assert entry(client, world.cera).status_code == expected
    assert _adjust(client, world.cera, -1).status_code == expected


def test_la_entrada_exige_csrf(world):
    logged_in_with_mfa(world.owner.user)
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.owner.user)
    body = {"request_key": str(uuid.uuid4()), "quantity": 1, "reason": "Compra"}
    url = reverse("api_product_entry", kwargs={"public_id": world.cera.public_id})

    rejected = client.post(url, body, content_type="application/json")
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)

    assert (rejected.status_code, rejected.json()["code"]) == (403, "csrf_failed")
    assert accepted.status_code == 201
