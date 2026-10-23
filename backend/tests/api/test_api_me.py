"""`me`: persona, barbería, rol, permisos de roles.py y sedes del alcance, sin nada de otra sede."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.tenancy.roles import ROLE_PERMISSIONS, Role
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", list(Role))
def test_los_permisos_de_me_son_los_de_roles_py(member, shop, role):
    membership = member(role, shop)
    client = logged_in_with_mfa(membership.user)

    me = client.get(reverse("api_me")).json()

    assert me["permissions"] == sorted(ROLE_PERMISSIONS[role])
    assert me["role"] == {"code": role.value, "label": role.label}
    assert me["barbershop"]["name"] == shop.trade_name


def test_el_cajero_de_centro_no_recibe_sedes_ni_datos_de_norte(cashier_client, norte):
    response = cashier_client.get(reverse("api_me"))
    branch = response.json()["branch"]

    assert [option["label"] for option in branch["options"]] == ["Centro"]
    assert branch["current_label"] == "Centro"
    assert (branch["mode"], branch["can_view_all"], branch["can_manage"]) == ("una", False, False)
    assert norte.name not in response.content.decode()
    assert str(norte.public_id) not in response.content.decode()
    assert norte.name not in cashier_client.get(reverse("api_navigation")).content.decode()


def test_el_dueno_ve_todas_sus_sedes_y_puede_elegir_todas(owner_client, norte):
    branch = owner_client.get(reverse("api_me")).json()["branch"]

    assert [option["label"] for option in branch["options"]] == ["Centro", "Norte"]
    assert branch["can_view_all"] is True
    assert branch["can_manage"] is True


def test_me_no_entrega_datos_de_otra_barberia(world, other_shop, member):
    stranger = member(Role.CASHIER, other_shop)
    client = Client()
    client.force_login(stranger.user)

    content = client.get(reverse("api_me")).content.decode()

    assert world.shop.trade_name not in content
    assert world.branch.name not in content
