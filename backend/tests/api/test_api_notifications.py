"""`notifications`: alertas reales, solo de lectura, por alcance de sede y con alertas.ver."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.alerts.models import Alert, AlertType
from apps.tenancy.roles import Role
from tests.frontend.conftest import logged_in_with_mfa

pytestmark = pytest.mark.django_db


def _alert(world, branch, product, *, days_ago: int = 0) -> Alert:
    alert = Alert.objects.create(
        alert_type=AlertType.OUT_OF_STOCK, product=product, branch=branch, message=f"{product.name} agotado"
    )
    if days_ago:
        Alert.objects.filter(pk=alert.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
    return alert


def _messages(data: dict) -> list[str]:
    return [item["message"] for group in data["groups"] for item in group["items"]]


def test_el_cajero_de_centro_solo_ve_las_alertas_de_centro(world, norte, cashier_client, owner_client):
    _alert(world, world.branch, world.cera)
    _alert(world, norte, world.cuchilla)

    mine = cashier_client.get(reverse("api_notifications")).json()
    owner_client.post(reverse("api_branch"), {"sede": "todas"}, content_type="application/json")
    everything = owner_client.get(reverse("api_notifications")).json()

    assert _messages(mine) == ["Cera agotado"]
    assert mine["unread"] == 1
    assert sorted(_messages(everything)) == ["Cera agotado", "Cuchilla agotado"]
    assert "Norte" not in str(mine)


def test_se_agrupan_en_hoy_y_anteriores(world, cashier_client):
    _alert(world, world.branch, world.cera)
    _alert(world, world.branch, world.cuchilla, days_ago=3)

    groups = cashier_client.get(reverse("api_notifications")).json()["groups"]

    assert [(group["title"], [item["message"] for item in group["items"]]) for group in groups] == [
        ("Hoy", ["Cera agotado"]),
        ("Anteriores", ["Cuchilla agotado"]),
    ]


def test_sin_alertas_no_hay_grupos(world, cashier_client):
    assert cashier_client.get(reverse("api_notifications")).json() == {"unread": 0, "groups": []}


def test_el_barbero_sin_alertas_ver_no_puede_leerlas(world):
    client = logged_in_with_mfa(world.ana_login.user)
    assert client.get(reverse("api_notifications")).status_code == 403


def test_es_solo_lectura(world, cashier_client):
    response = cashier_client.post(reverse("api_notifications"), {}, content_type="application/json")
    assert response.status_code == 405


def test_el_consultor_las_ve(world, member):
    viewer = member(Role.VIEWER, world.shop)
    assert logged_in_with_mfa(viewer.user).get(reverse("api_notifications")).status_code == 200
