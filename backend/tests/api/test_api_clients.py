"""Clientes en la API: la persona es de la barbería y su historial, nivel y fiados de cada sede; la política de
datos al crear, los duplicados, la edición con su permiso y los datos personales enmascarados."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.clients.board import PAGE_SIZE
from apps.clients.forms import INVALID_MOBILE
from apps.clients.models import Client as ClientRecord
from apps.clients.services import MISSING_POLICY
from apps.legal.models import LegalDocument
from apps.receivables import services as receivables
from apps.tenancy.roles import Role
from tests.api.sales_support import choose_branch, credit, new_client, post, sell
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

NEW = {"full_name": "Pedro Ríos", "phone": "310 555 1234", "document": "1.020.304", "consent": True}


def _as(member_fixture, world, role: Role) -> Client:
    client = Client()
    client.force_login(member_fixture(role, world.shop, email=f"{role}-clientes@a.test").user)
    return client


def _detail(client: Client, customer) -> dict:
    return client.get(reverse("api_client", kwargs={"public_id": customer.public_id})).json()


def test_la_lista_trae_los_clientes_con_actividad_en_la_sede_con_sus_cifras(world, cashier_client):
    sell(world, cashier_client, customer=world.laura)
    new_client(world, "Sin Visitas")

    listing = cashier_client.get(reverse("api_clients")).json()

    assert [row["name"] for row in listing["results"]] == ["Laura Gómez"]
    row = listing["results"][0]
    assert (row["visits"], row["spent_recent"], row["debt"], row["level"]) == (1, "25000.00", "0.00", "new")
    assert row["phone"] == "300 *** 4567"
    assert listing["page_size"] == PAGE_SIZE
    assert {level["value"]: level["count"] for level in listing["levels"]}[""] == 1


def test_los_filtros_de_nivel_y_orden_van_en_la_consulta(world, cashier_client):
    sell(world, cashier_client, customer=world.laura)
    credit(world, new_client(world, "Debe Mucho"), total="40000")

    debtors = cashier_client.get(reverse("api_clients"), {"nivel": "debtor"}).json()
    by_debt = cashier_client.get(reverse("api_clients"), {"orden": "deuda"}).json()
    invalid = cashier_client.get(reverse("api_clients"), {"nivel": "rey"}).json()

    assert [row["name"] for row in debtors["results"]] == ["Debe Mucho"]
    assert [row["name"] for row in by_debt["results"]] == ["Debe Mucho", "Laura Gómez"]
    assert (invalid["level"], len(invalid["results"])) == ("", 2)  # un valor inválido vuelve al de siempre


def test_el_cajero_de_centro_no_ve_los_clientes_ni_el_historial_de_norte(world, norte, cashier_client):
    credit(world, world.laura, branch=norte)

    listing = cashier_client.get(reverse("api_clients")).json()
    detail = _detail(cashier_client, world.laura)

    assert listing["results"] == []
    assert (detail["activity"], detail["receivables"]) == (None, [])


def test_la_busqueda_encuentra_un_cliente_de_otra_sede_sin_sus_datos_de_esa_sede(world, norte, cashier_client):
    credit(world, world.laura, branch=norte, total="90000")

    found = cashier_client.get(reverse("api_clients"), {"q": "laura"}).json()["results"]

    assert found == [
        {
            "id": str(world.laura.public_id),
            "name": "Laura Gómez",
            "phone": "300 *** 4567",
            "has_activity": False,
            "level": None,
            "level_label": "Sin visitas en la sede",
            "visits": None,
            "last_visit": None,
            "spent_recent": None,
            "debt": None,
        }
    ]
    assert "90000" not in str(_detail(cashier_client, world.laura))


def test_en_todas_las_sedes_el_nivel_varia_por_sede(world, norte, owner_client):
    credit(world, world.laura)
    assert post(owner_client, "api_branch", {"sede": "todas"}).status_code == 200

    row = owner_client.get(reverse("api_clients")).json()["results"][0]
    detail = _detail(owner_client, world.laura)

    assert (row["level"], row["level_label"]) == (None, "Varía por sede")
    assert detail["activity"]["level_label"] == "Varía por sede"
    assert detail["actions"]["new_order"] is False


def test_la_ficha_trae_el_nivel_las_visitas_y_los_fiados_de_la_sede(world, cashier_client):
    order = sell(world, cashier_client, customer=world.laura)
    debt = credit(world, world.laura, total="10000")

    detail = _detail(cashier_client, world.laura)

    activity = detail["activity"]
    assert (activity["level"], activity["visits"], activity["balance"]) == ("debtor", 1, "10000.00")
    assert activity["open_debt"] == str(debt.public_id)
    assert activity["last_visits"][0]["id"] == str(order.public_id)
    assert [row["id"] for row in detail["receivables"]] == [str(debt.public_id)]
    assert detail["actions"] == {"edit": True, "new_order": True}


def test_el_celular_sale_enmascarado_el_documento_nunca_y_el_correo_solo_a_quien_edita(
    world, member, owner_client, legal_documents
):
    post(owner_client, "api_client_create", {**NEW, "email": "pedro@correo.test"})
    created = ClientRecord.objects.get(full_name="Pedro Ríos")
    viewer = _as(member, world, Role.VIEWER)

    for_owner, for_viewer = _detail(owner_client, created), _detail(viewer, created)

    assert for_owner["phone"] == "310 *** 1234"
    assert "1020304" not in str(for_owner) and "3105551234" not in str(for_owner)
    assert (for_owner["email"], for_viewer["email"]) == ("pedro@correo.test", None)


def test_crear_exige_la_autorizacion_de_la_politica_vigente(world, cashier_client, legal_documents):
    without_consent = post(cashier_client, "api_client_create", {**NEW, "consent": False})
    created = post(cashier_client, "api_client_create", NEW)

    assert without_consent.status_code == 400
    assert list(without_consent.json()["field_errors"]) == ["consent"]
    assert created.status_code == 201
    assert created.json()["phone"] == "310 *** 1234"
    assert ClientRecord.objects.get(full_name="Pedro Ríos").data_policy_version == "1.0"


def test_sin_politica_publicada_no_se_crea_y_la_lista_lo_avisa(world, cashier_client):
    LegalDocument.objects.filter(kind=LegalDocument.Kind.DATA_POLICY).delete()

    response = post(cashier_client, "api_client_create", NEW)

    assert (response.status_code, response.json()["code"]) == (400, "missing_policy")
    assert response.json()["detail"] == MISSING_POLICY
    assert cashier_client.get(reverse("api_clients")).json()["data_policy"] is None
    assert not ClientRecord.objects.filter(full_name="Pedro Ríos").exists()


def test_la_lista_trae_la_politica_vigente_para_el_formulario(world, cashier_client, legal_documents):
    policy = cashier_client.get(reverse("api_clients")).json()["data_policy"]

    assert policy == {"version": "1.0", "url": "/legal/tratamiento-de-datos/"}


def test_un_duplicado_responde_solo_el_nombre_del_que_ya_existe(world, cashier_client, legal_documents):
    same_phone = post(cashier_client, "api_client_create", {**NEW, "phone": "300 123 4567"})
    same_name = post(cashier_client, "api_client_create", {**NEW, "full_name": "Laura Gómez", "phone": ""})
    confirmed = post(
        cashier_client, "api_client_create", {**NEW, "full_name": "Laura Gómez", "phone": "", "other_person": True}
    )

    assert (same_phone.json()["code"], same_phone.json()["detail"]) == (
        "duplicate_client",
        "Ya existe un cliente con ese teléfono o documento: Laura Gómez.",
    )
    assert same_name.json()["code"] == "possible_duplicate"
    assert "Laura Gómez" in same_name.json()["detail"]
    assert confirmed.status_code == 201


def test_un_celular_que_no_es_colombiano_se_rechaza_con_el_mensaje_de_django(world, cashier_client, legal_documents):
    response = post(cashier_client, "api_client_create", {**NEW, "phone": "12345"})

    assert response.status_code == 400
    assert response.json()["field_errors"] == {"phone": [INVALID_MOBILE]}


def test_editar_cambia_la_identidad_y_un_celular_vacio_no_lo_borra(world, cashier_client):
    body = {"full_name": "Laura Gómez Ríos", "notes": "Degradado bajo", "phone": "", "document": ""}

    response = post(cashier_client, "api_client_edit", body, public_id=world.laura.public_id)

    world.laura.refresh_from_db()
    assert response.status_code == 200
    assert (world.laura.full_name, world.laura.notes, world.laura.phone) == (
        "Laura Gómez Ríos",
        "Degradado bajo",
        "573001234567",
    )
    assert response.json()["notes"] == "Degradado bajo"


def test_cada_rol_crea_y_edita_segun_roles_py(world, member, legal_documents):
    viewer, barber = _as(member, world, Role.VIEWER), _as(member, world, Role.BARBER)
    edit = {"full_name": "Otra"}

    assert viewer.get(reverse("api_clients")).status_code == 200
    assert post(viewer, "api_client_create", NEW).status_code == 403
    assert post(viewer, "api_client_edit", edit, public_id=world.laura.public_id).status_code == 403
    assert post(barber, "api_client_create", NEW).status_code == 201
    assert _detail(viewer, world.laura)["actions"]["edit"] is False


def test_crear_exige_csrf(world, legal_documents):
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)

    rejected = post(client, "api_client_create", NEW)
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(reverse("api_client_create"), NEW, content_type="application/json", HTTP_X_CSRFTOKEN=token)

    assert rejected.status_code == 403
    assert accepted.status_code == 201


def test_una_ficha_que_no_existe_responde_404_con_la_forma_comun(world, cashier_client):
    response = cashier_client.get(reverse("api_client", kwargs={"public_id": "00000000-0000-0000-0000-000000000001"}))

    assert response.json() == {"detail": "No encontramos lo que buscas.", "code": "not_found", "field_errors": {}}


def test_choose_branch_cambia_la_ficha_a_la_sede_elegida(world, norte, owner_client):
    credit(world, world.laura, branch=norte, total="30000")

    choose_branch(owner_client, world.branch)
    in_centro = _detail(owner_client, world.laura)
    choose_branch(owner_client, norte)
    in_norte = _detail(owner_client, world.laura)

    assert in_centro["activity"] is None
    assert in_norte["activity"]["balance"] == "30000.00"


def test_un_fiado_anulado_sale_en_la_ficha_como_anulado(world, cashier_client):
    debt = credit(world, world.laura)
    receivables.cancel_receivable(
        world.owner, debt.public_id, scope=scope_of(world.owner, world.branch), reason="Error"
    )

    rows = _detail(cashier_client, world.laura)["receivables"]

    assert [(row["due_text"], row["balance"]) for row in rows] == [("Anulado", "0.00")]


def test_un_correo_invalido_se_rechaza_en_su_campo(world, cashier_client, legal_documents):
    response = post(cashier_client, "api_client_create", {**NEW, "email": "no-es-correo"})

    assert response.status_code == 400
    assert list(response.json()["field_errors"]) == ["email"]
