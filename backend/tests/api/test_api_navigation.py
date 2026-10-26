"""`navigation`: los mismos grupos e ítems de navigation.py, filtrados por el permiso del rol."""

import pytest
from django.urls import reverse

from apps.core.navigation import ADMINISTRATION, NEW_ACTIONS, SIDEBAR, NavGroup, NavItem
from apps.tenancy.roles import Role, role_has_permission
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db


def _visible(item: NavItem, role: Role) -> bool:
    return item.permission is None or role_has_permission(role, item.permission)


def _expected(groups: tuple[NavGroup, ...], role: Role) -> list[tuple[str, list[str]]]:
    visible = [(group.title, [item.label for item in group.items if _visible(item, role)]) for group in groups]
    return [(title, labels) for title, labels in visible if labels]


def _received(groups: list[dict]) -> list[tuple[str, list[str]]]:
    return [(group["title"], [item["label"] for item in group["items"]]) for group in groups]


@pytest.fixture
def navigation_as(member, shop):
    def _get(role: Role) -> dict:
        return logged_in_with_mfa(member(role, shop).user).get(reverse("api_navigation")).json()

    return _get


@pytest.mark.parametrize("role", list(Role))
def test_cada_rol_recibe_solo_los_items_de_sus_permisos(navigation_as, role):
    navigation = navigation_as(role)

    assert _received(navigation["sidebar"]) == _expected(SIDEBAR, role)
    assert _received(navigation["administration"]) == _expected(ADMINISTRATION, role)
    assert [item["label"] for item in navigation["new_actions"]] == [
        item.label for item in NEW_ACTIONS if _visible(item, role)
    ]


def test_el_estado_dice_si_hay_pantalla_pronto_o_proximamente(navigation_as):
    navigation = navigation_as(Role.OWNER)
    sidebar = {item["label"]: item for group in navigation["sidebar"] for item in group["items"]}
    administration = [item for group in navigation["administration"] for item in group["items"]]

    assert sidebar["Comandas"] == {
        "label": "Comandas",
        "icon": "receipt",
        "url": "/comandas/",
        "app_path": "/comandas",  # desde la fase R2, en la app de React; la de Django queda de respaldo
        "status": "enlace",
    }
    assert sidebar["Agenda"] == {
        "label": "Agenda",
        "icon": "calendar",
        "url": None,
        "app_path": None,
        "status": "pronto",
    }
    assert sidebar["Tablero"]["app_path"] == "/"  # el tablero ya existe en la app de React
    assert {item["status"] for item in administration} == {"proximamente"}
    assert all(item["url"] is None for item in administration)


def test_el_contador_de_alertas_solo_llega_con_alertas_ver(navigation_as):
    assert navigation_as(Role.OWNER)["unread_alerts"] == 0
    assert navigation_as(Role.BARBER)["unread_alerts"] is None


def test_el_resumen_de_administracion_solo_llega_con_items_y_cada_dato_con_su_permiso(navigation_as):
    owner = navigation_as(Role.OWNER)["administration_summary"]
    cashier = navigation_as(Role.CASHIER)

    assert owner["branches"] == {"active": 1, "limit": 1}
    assert owner["can_see_audit"] is True
    assert (cashier["administration"], cashier["administration_summary"]) == ([], None)
