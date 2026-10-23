"""El marco de la aplicación (fase F1): qué ve cada rol en Administración, la barra lateral y el selector de sede."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.alerts import selectors as alert_selectors
from apps.alerts import services as alerts
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.sales.selectors import local_today
from apps.tenancy.models import Branch, MembershipBranch
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.frontend.conftest import logged_in_with_mfa
from tests.frontend.html_support import elements, forms

pytestmark = pytest.mark.django_db

ADMIN_GROUPS = ["Barbería", "Equipo", "Catálogo y precios", "Clientes y fiados", "Seguridad y datos", "Cuenta y plan"]
WITH_SCREEN = {"Tablero", "Comandas", "Caja", "Clientes", "Fiados"}
ALL_SIDEBAR = {
    "Operación": ["Tablero", "Agenda", "Comandas", "Caja"],
    "Clientes": ["Clientes", "Fiados", "Reseñas"],
    "Catálogo": ["Servicios", "Inventario"],
    "Análisis": ["Reportes", "Comparativo de sedes"],
}


def _page(world, role: str):
    """La página de inicio de cada rol de `world`; dueño y administrador entran con 2FA."""
    if role == "owner":
        return logged_in_with_mfa(world.owner.user).get(reverse("home"))
    client = Client()
    client.force_login({"cashier": world.cashier, "barber": world.ana_login}[role].user)
    return client.get(reverse("home"))


def _sidebar(page) -> dict:
    return {group["title"]: [item["label"] for item in group["items"]] for group in page.context["shell"]["sidebar"]}


def _admin_groups(page) -> list[str]:
    panel = page.context["shell"]["admin"]
    return [group["title"] for group in panel["groups"]] if panel else []


def test_el_dueno_ve_todo_administracion_y_toda_la_barra_lateral(world):
    page = _page(world, "owner")
    assert _admin_groups(page) == ADMIN_GROUPS
    assert _sidebar(page) == ALL_SIDEBAR
    assert set(page.context["shell"]["admin"]["summary"]) == {"branches", "members", "audit"}


def test_el_administrador_no_ve_lo_exclusivo_del_dueno(world, member, in_shop):
    admin = member(Role.ADMIN, in_shop)
    page = logged_in_with_mfa(admin.user).get(reverse("home"))

    account_and_plan = next(g for g in page.context["shell"]["admin"]["groups"] if g["title"] == "Cuenta y plan")
    assert [item["label"] for item in account_and_plan["items"]] == ["Textos legales", "Soporte"]
    labels = {item["label"] for group in page.context["shell"]["admin"]["groups"] for item in group["items"]}
    assert "Datos personales" not in labels  # anonimizar clientes es solo del dueño
    assert _sidebar(page) == ALL_SIDEBAR


def test_el_cajero_no_ve_administracion_y_su_barra_es_de_caja(world):
    page = _page(world, "cashier")
    assert page.context["shell"]["admin"] is None
    assert 'aria-controls="menu-administracion"' not in page.content.decode()
    assert _sidebar(page) == {
        "Operación": ["Tablero", "Agenda", "Comandas", "Caja"],
        "Clientes": ["Clientes", "Fiados", "Reseñas"],
        "Catálogo": ["Servicios", "Inventario"],
        "Análisis": ["Reportes"],
    }


def test_el_barbero_no_ve_administracion_caja_fiados_ni_analisis(world):
    page = _page(world, "barber")
    assert page.context["shell"]["admin"] is None
    assert _sidebar(page) == {
        "Operación": ["Tablero", "Agenda", "Comandas"],
        "Clientes": ["Clientes", "Reseñas"],
        "Catálogo": ["Servicios", "Inventario"],
    }


def test_lo_que_no_tiene_pantalla_no_es_un_enlace(world):
    page = _page(world, "owner")
    hrefs = {attrs.get("href") for tag, attrs, _ in elements(page.content.decode()) if tag == "a"}
    soon = [
        item
        for group in page.context["shell"]["sidebar"] + page.context["shell"]["admin"]["groups"]
        for item in group["items"]
        if item["label"] not in WITH_SCREEN
    ]
    assert all(item["url"] is None for item in soon)
    assert hrefs <= {
        reverse("home"),
        reverse("orders_board"),
        reverse("orders_new"),
        reverse("orders_quick"),
        reverse("cash_register"),
        reverse("cash_register") + "#gasto",
        reverse("clients_board"),
        reverse("clients_new"),
        reverse("receivables_board"),
        reverse("mfa_index"),
        reverse("reports_export") + f"?mes={local_today(world.owner):%Y-%m}",
        *(reverse("legal_document", args=[slug]) for slug in ("terminos", "privacidad", "cookies")),
    }


# ── Selector de sede ─────────────────────────────────────────────────────────


@pytest.fixture
def norte(world):
    return Branch.objects.create(name="Norte")


def _choices(page) -> list[str]:
    menu = page.context["shell"]["branches"]
    return (["Todas"] if menu["all"] else []) + [option["label"] for option in menu["options"]]


def test_el_cajero_de_centro_no_ve_norte_ni_todas(world, norte):
    assert _choices(_page(world, "cashier")) == ["Centro"]


def test_el_dueno_ve_las_dos_sedes_y_todas(world, norte):
    page = _page(world, "owner")
    assert _choices(page) == ["Todas", "Centro", "Norte"]
    assert page.context["shell"]["branches"]["manage"]  # "Gestionar sedes", como Próximamente


def test_cambiar_de_sede_es_post_con_csrf_y_redirige(world, norte):
    page = _page(world, "owner")
    switches = [form for form in forms(page.content.decode()) if form["action"] == reverse("switch_branch")]
    assert len(switches) == 3 and all(f["method"] == "post" and "csrfmiddlewaretoken" in f["fields"] for f in switches)

    client = logged_in_with_mfa(world.cashier.user)
    response = client.post(reverse("switch_branch"), {"sede": str(world.branch.public_id), "next": "/"})
    assert (response.status_code, response["Location"]) == (302, "/")
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(world.cashier.user)
    assert strict.post(reverse("switch_branch"), {"sede": str(world.branch.public_id)}).status_code == 403


# ── Cuenta y alertas ─────────────────────────────────────────────────────────


def test_cerrar_sesion_por_get_no_cierra_la_sesion(world):
    client = Client()
    client.force_login(world.cashier.user)
    client.get(reverse("account_logout"))
    assert client.get(reverse("home")).wsgi_request.user.is_authenticated
    client.post(reverse("account_logout"))
    assert not client.get(reverse("home")).wsgi_request.user.is_authenticated


def test_la_campana_cuenta_las_alertas_sin_leer_del_alcance(client, make_shop, member):
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


def test_las_pantallas_son_enlaces_y_nuevo_solo_trae_lo_permitido(world):
    owner, cashier, barber = _page(world, "owner"), _page(world, "cashier"), _page(world, "barber")

    links = {item["label"]: item["url"] for group in owner.context["shell"]["sidebar"] for item in group["items"]}
    assert (links["Comandas"], links["Caja"]) == (reverse("orders_board"), reverse("cash_register"))
    everything = ["Nueva comanda", "Cobro rápido", "Registrar gasto", "Nuevo cliente", "Abono a fiado"]
    assert [a["label"] for a in owner.context["shell"]["new_actions"]] == everything
    assert [a["label"] for a in cashier.context["shell"]["new_actions"]] == everything
    assert [a["label"] for a in barber.context["shell"]["new_actions"]] == [
        "Nueva comanda",
        "Cobro rápido",
        "Nuevo cliente",
    ]


def test_el_detalle_de_una_comanda_deja_activo_comandas(world):
    client = Client()
    client.force_login(world.cashier.user)
    page = client.get(reverse("orders_new"))
    active = [item["label"] for group in page.context["shell"]["sidebar"] for item in group["items"] if item["active"]]
    assert active == ["Comandas"]
