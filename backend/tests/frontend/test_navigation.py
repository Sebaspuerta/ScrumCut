"""La barra y el menú muestran solo lo que el rol puede ver según roles.py."""

import pytest
from django.urls import reverse

from apps.alerts import selectors as alert_selectors
from apps.alerts import services as alerts
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.sales.selectors import local_today
from apps.tenancy.models import Branch, MembershipBranch
from apps.tenancy.roles import Role
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db

ADMIN = ["Gestión de barberos", "Usuarios y roles", "Auditoría", "Ajustes"]
MODULES = ["Tablero", "Comandas", "Caja", "Clientes", "Servicios", "Inventario", "Fiados", "Reportes", "Alertas"]


def _labels(response, group: str) -> list[str]:
    return [link["label"] for link in response.context["shell"][group]]


def test_el_dueno_ve_la_administracion_y_los_nueve_modulos(owner_page):
    assert _labels(owner_page, "admin_links") == ADMIN
    assert _labels(owner_page, "module_links") == MODULES
    page = owner_page.content.decode()
    # aria-label con el nombre: es lo que se lee cuando el menú se contrae a solo íconos.
    assert all(f'aria-label="{label}"' in page for label in ADMIN + MODULES)


def test_el_barbero_no_ve_administracion_caja_reportes_ni_fiados(barber_page):
    assert _labels(barber_page, "admin_links") == []
    assert _labels(barber_page, "module_links") == ["Tablero", "Comandas", "Clientes", "Servicios", "Inventario"]
    assert 'aria-label="Administración"' not in barber_page.content.decode()


def test_solo_el_tablero_es_un_enlace_y_los_demas_estan_atenuados(owner_page):
    links = {link["label"]: link for link in owner_page.context["shell"]["module_links"]}
    assert links["Tablero"]["url"] == reverse("home") and links["Tablero"]["active"]
    assert all(link["url"] is None for label, link in links.items() if label != "Tablero")
    assert owner_page.content.decode().count('aria-disabled="true"') >= len(ADMIN) + len(MODULES) - 1


def test_la_campana_cuenta_las_alertas_sin_leer(client, make_shop, member):
    shop = make_shop("a")
    owner, cashier = member(Role.OWNER, shop), member(Role.CASHIER, shop)
    with tenant_context(shop.pk):
        MembershipBranch.objects.create(membership=cashier, branch=Branch.objects.get())
        for name in ("Cera", "Gel"):
            inventory.create_product(owner, {"name": name, "product_type": "venta"}, scope=scope_of(owner))
        alerts.generate_alerts(local_today(owner))
        expected = alert_selectors.unread_count(cashier, scope=scope_of(cashier))
    client.force_login(cashier.user)

    response = client.get(reverse("home"))

    assert expected == 2
    assert response.context["shell"]["unread_alerts"] == expected
    assert f'aria-label="Alertas: {expected} sin leer"' in response.content.decode()
