"""Página del tablero: permisos, período, exportación, aislamiento y consultas acotadas."""

import re
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from openpyxl import load_workbook

from apps.cash import services as cash
from apps.core.tenant_context import tenant_context
from apps.sales import services as sales
from apps.sales.selectors import local_today
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role
from tests.frontend.conftest import logged_in_with_mfa
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

MONEY_TABLES = ("cash_", "receivables_", "sales_payment")


@pytest.fixture
def owner_client(world):
    return logged_in_with_mfa(world.owner.user)


def test_el_tablero_muestra_los_datos_reales(world, owner_client):
    sell(world, world.ana, service=world.corte)

    page = owner_client.get(reverse("home"))
    html = page.content.decode()

    assert page.context["state"] == "ready"
    assert "Ingresos de hoy" in html and "$25.000" in html
    assert "Sin referencia" in html  # la semana anterior no vendió a esta hora
    assert '<script id="towers-data" type="application/json">' in html


def test_los_pasos_en_cero_de_la_cascada_van_sin_signo(world, owner_client):
    html = owner_client.get(reverse("home")).content.decode()  # caja abierta, sin movimientos
    amounts = re.findall(r'cascade__amount num">([^<]*)<', html)
    assert amounts and "$0" in amounts
    assert not [amount for amount in amounts if amount in ("+$0", "−$0")]


def test_el_barbero_ve_solo_sus_cortes_y_ninguna_cifra_de_dinero(world):
    sell(world, world.ana, service=world.corte)
    client = Client()
    client.force_login(world.ana_login.user)

    with CaptureQueriesContext(connection) as queries:
        page = client.get(reverse("home"))
    html = page.content.decode()

    assert page.context["state"] == "cuts" and "Mis cortes de hoy" in html
    assert re.search(r'kpi__value num">\s*1\s*<', html)
    assert "$" not in html
    assert not [q["sql"] for q in queries.captured_queries if any(table in q["sql"] for table in MONEY_TABLES)]


def test_exportar_exige_el_permiso_y_responde_un_xlsx(world, owner_client):
    sell(world, world.ana, service=world.corte)
    cashier = Client()
    cashier.force_login(world.cashier.user)

    assert cashier.get(reverse("reports_export")).status_code == 403
    response = owner_client.get(reverse("reports_export"), {"periodo": "mes"})

    today = local_today(world.owner)
    assert response["Content-Type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml")
    assert response["Content-Disposition"] == (
        f'attachment; filename="scrumcut-{world.shop.slug}-centro-{today.replace(day=1):%Y%m%d}-{today:%Y%m%d}.xlsx"'
    )
    assert load_workbook(BytesIO(response.content)).sheetnames[0] == "Panorama"


def _sales_in_export(client, branch) -> list:
    response = client.get(reverse("reports_export"), {"sede": str(branch.public_id)})
    rows = load_workbook(BytesIO(response.content))["Ventas"].iter_rows(min_row=5, values_only=True)
    return sorted(row[3] for row in rows)


def test_exportar_una_sede_no_incluye_las_ventas_de_otra(world, owner_client):
    norte = Branch.objects.create(name="Norte")
    cash.open_session(world.cashier, norte.public_id, opening_amount=Decimal("0"))
    sell(world, world.ana, service=world.corte)  # en Centro
    sales.quick_register(
        world.cashier, norte.public_id, barber=world.beto.public_id, method="efectivo", product=world.cera.public_id
    )

    assert _sales_in_export(owner_client, world.branch) == ["Corte"]
    assert _sales_in_export(owner_client, norte) == ["Cera"]
    response = owner_client.get(reverse("reports_export"), {"sede": str(norte.public_id)})
    assert "-norte-" in response["Content-Disposition"]


def test_un_periodo_invalido_cae_en_los_ultimos_30_dias(world, owner_client):
    dashboard = owner_client.get(reverse("home"), {"periodo": "siempre"}).context["dashboard"]
    today = local_today(world.owner)
    assert (dashboard["date_from"], dashboard["date_to"]) == (today - timedelta(days=29), today)


def test_un_rango_de_mas_de_366_dias_se_rechaza(world, owner_client):
    today = local_today(world.owner)
    params = {"periodo": "rango", "desde": (today - timedelta(days=366)).isoformat(), "hasta": today.isoformat()}

    page = owner_client.get(reverse("home"), params)

    assert page.context["form"].errors
    assert page.context["dashboard"]["date_from"] == today - timedelta(days=29)
    assert "no puede pasar de 366 días" in page.content.decode()


def test_cada_barberia_ve_solo_sus_ventas(world, member, other_shop):
    sell(world, world.ana, service=world.corte)
    with tenant_context(other_shop.pk):
        theirs = logged_in_with_mfa(member(Role.OWNER, other_shop).user)

    dashboard = theirs.get(reverse("home")).context["dashboard"]

    assert not dashboard["has_sales"] and dashboard["kpis"]["income"]["value"] == 0


def test_el_tablero_hace_un_numero_acotado_de_consultas(world, owner_client, django_assert_max_num_queries):
    for _ in range(3):
        sell(world, world.ana, service=world.corte)
        sell(world, world.beto, product=world.cera)
    with django_assert_max_num_queries(30):  # hoy son 28 y no crecen con las ventas
        owner_client.get(reverse("home"))
