"""`branch`: el cambio de sede por POST pasa por `choose_branch`; una sede no permitida responde 403."""

import pytest
from django.urls import reverse

from apps.tenancy.middleware import BRANCH_SESSION_KEY
from apps.tenancy.models import Membership

pytestmark = pytest.mark.django_db


def _switch(client, sede: str):
    return client.post(reverse("api_branch"), {"sede": sede}, content_type="application/json")


def test_el_dueno_cambia_a_norte_y_queda_como_su_ultima_sede(world, owner_client, norte):
    response = _switch(owner_client, str(norte.public_id))

    assert response.status_code == 200
    assert response.json()["current_label"] == "Norte"
    assert owner_client.session[BRANCH_SESSION_KEY] == str(norte.public_id)
    assert owner_client.get(reverse("api_me")).json()["branch"]["current_label"] == "Norte"
    assert Membership.objects.get(pk=world.owner.pk).last_branch_id == norte.pk


def test_el_dueno_puede_elegir_todas(owner_client, norte):
    response = _switch(owner_client, "todas")

    assert response.status_code == 200
    assert response.json()["mode"] == "todas"
    assert response.json()["current_label"] == "Todas las sedes"


@pytest.mark.parametrize("sede", ["norte", "todas", "no-es-una-sede"])
def test_el_cajero_de_centro_no_puede_cambiar_a_lo_que_no_le_permite_choose_branch(world, cashier_client, norte, sede):
    choice = str(norte.public_id) if sede == "norte" else sede

    response = _switch(cashier_client, choice)

    assert response.status_code == 403
    assert cashier_client.get(reverse("api_me")).json()["branch"]["current_label"] == "Centro"
    assert Membership.objects.get(pk=world.cashier.pk).last_branch_id != norte.pk


def test_sin_el_campo_sede_responde_400_con_el_error_del_campo(cashier_client):
    response = cashier_client.post(reverse("api_branch"), {}, content_type="application/json")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Revisa los datos enviados.",
        "code": "invalid",
        "field_errors": {"sede": ["Este campo es requerido."]},
    }
