"""`me/preferences`: el tema se guarda en el servidor, exige CSRF y solo acepta system, light o dark."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _patch(client, theme: str, **extra):
    return client.patch(reverse("api_preferences"), {"theme": theme}, content_type="application/json", **extra)


@pytest.mark.parametrize("theme", ["dark", "light", "system"])
def test_el_tema_se_guarda_y_me_lo_devuelve(world, cashier_client, theme):
    response = _patch(cashier_client, theme)

    assert response.status_code == 200
    assert response.json() == {"theme": theme}
    assert User.objects.get(pk=world.cashier.user.pk).theme == theme
    assert cashier_client.get(reverse("api_me")).json()["user"]["theme"] == theme


@pytest.mark.parametrize("theme", ["blue", "", "DARK"])
def test_solo_acepta_system_light_o_dark(world, cashier_client, theme):
    response = _patch(cashier_client, theme)

    assert response.status_code == 400
    assert User.objects.get(pk=world.cashier.user.pk).theme == "system"


def test_exige_csrf(world):
    client = Client(enforce_csrf_checks=True)
    client.force_login(world.cashier.user)

    rejected = _patch(client, "dark")
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = _patch(client, "dark", HTTP_X_CSRFTOKEN=token)

    assert rejected.status_code == 403
    assert accepted.status_code == 200


def test_sin_sesion_no_se_puede(client):
    assert _patch(client, "dark").status_code in {401, 403}


def test_la_pagina_de_la_app_llega_con_el_tema_de_la_persona(world, cashier_client, settings, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"src/main.tsx": {"file": "assets/main.js"}}', encoding="utf-8")
    settings.REACT_APP_MANIFEST = manifest

    system = cashier_client.get(reverse("react_app")).content.decode()
    _patch(cashier_client, "dark")
    dark = cashier_client.get(reverse("react_app")).content.decode()

    assert "data-theme" not in system  # sin elección, manda prefers-color-scheme
    assert '<html lang="es" data-theme="dark">' in dark
