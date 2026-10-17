"""Un cajero de Centro no ve Norte por ninguna URL, ni con la sesión ni con el POST alterados (S2)."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.sales import services as sales
from apps.tenancy.branch_scope import ALL
from apps.tenancy.middleware import BRANCH_SESSION_KEY
from apps.tenancy.models import Membership
from tests.conftest import scope_of
from tests.frontend.conftest import logged_in_with_mfa
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db


@pytest.fixture
def cashier_client(world) -> Client:
    client = Client()
    client.force_login(world.cashier.user)
    return client


@pytest.fixture
def sold_in_both(world, norte):
    """25 000 en Centro (por el cajero) y 15 000 en Norte (por el dueño)."""
    sell(world, world.ana, service=world.corte)
    sales.quick_register(
        world.owner,
        scope_of(world.owner, norte),
        barber=world.beto.public_id,
        method="efectivo",
        service=world.barba.public_id,
    )
    return norte


def _income(page) -> Decimal:
    return page.context["dashboard"]["kpis"]["income"]["value"]


def test_el_cajero_de_centro_solo_ve_centro_en_el_tablero(cashier_client, sold_in_both):
    page = cashier_client.get(reverse("home"))

    assert page.wsgi_request.branch_scope.branch.name == "Centro"
    assert _income(page) == Decimal("25000")


def test_el_parametro_sede_de_la_url_ya_no_cambia_nada(cashier_client, sold_in_both):
    page = cashier_client.get(reverse("home"), {"sede": str(sold_in_both.public_id)})
    assert _income(page) == Decimal("25000")


def test_con_la_sesion_alterada_el_cajero_sigue_en_centro(cashier_client, sold_in_both):
    session = cashier_client.session
    session[BRANCH_SESSION_KEY] = str(sold_in_both.public_id)
    session.save()

    page = cashier_client.get(reverse("home"))

    assert page.wsgi_request.branch_scope.branch.name == "Centro" and _income(page) == Decimal("25000")
    assert cashier_client.session[BRANCH_SESSION_KEY] != str(sold_in_both.public_id)


@pytest.mark.parametrize("choice", ["norte", ALL, "no-es-una-sede"])
def test_cambiar_a_una_sede_no_permitida_responde_403(world, cashier_client, sold_in_both, choice):
    sede = str(sold_in_both.public_id) if choice == "norte" else choice
    response = cashier_client.post(reverse("switch_branch"), {"sede": sede})

    assert response.status_code == 403
    assert cashier_client.get(reverse("home")).wsgi_request.branch_scope.branch.name == "Centro"


def test_cambiar_de_sede_la_guarda_en_la_sesion_y_como_ultima_usada(world, sold_in_both):
    owner = logged_in_with_mfa(world.owner.user)

    response = owner.post(reverse("switch_branch"), {"sede": str(sold_in_both.public_id), "next": "/?periodo=mes"})

    assert response.status_code == 302 and response.url == "/?periodo=mes"
    assert owner.session[BRANCH_SESSION_KEY] == str(sold_in_both.public_id)
    assert Membership.objects.get(pk=world.owner.pk).last_branch == sold_in_both
    assert _income(owner.get(reverse("home"))) == Decimal("15000")


@pytest.mark.parametrize("target", ["https://evil.example/robar", "//evil.example/", "javascript:alert(1)"])
def test_la_vuelta_tras_cambiar_de_sede_no_sale_del_sitio(world, sold_in_both, target):
    owner = logged_in_with_mfa(world.owner.user)
    response = owner.post(reverse("switch_branch"), {"sede": ALL, "next": target})

    assert response.status_code == 302 and response.url == reverse("home")


def test_cambiar_de_sede_exige_csrf(world, sold_in_both):
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)

    assert client.post(reverse("switch_branch"), {"sede": str(world.branch.public_id)}).status_code == 403


def test_cambiar_de_sede_solo_por_post(world, cashier_client):
    assert cashier_client.get(reverse("switch_branch")).status_code == 405


def test_el_cajero_no_exporta_y_el_dueno_exporta_el_consolidado_sin_sede(world, cashier_client, sold_in_both):
    assert cashier_client.get(reverse("reports_export")).status_code == 403

    owner = logged_in_with_mfa(world.owner.user)
    response = owner.get(reverse("reports_export"))
    assert owner.get(reverse("home")).wsgi_request.branch_scope.is_all
    disposition = response["Content-Disposition"]
    assert "-centro-" not in disposition and "-norte-" not in disposition  # en "todas", sin sede
