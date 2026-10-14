"""Avisos del sistema: diseño por nivel, cierre sin depender de JS y sin el aviso de inicio de sesión de allauth."""

import pytest
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.urls import reverse

from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD
from tests.frontend.html_support import elements

pytestmark = pytest.mark.django_db


def _notices(messages: list[Message]) -> tuple[list[dict], str]:
    html = render_to_string("layout/messages.html", {"messages": messages})
    return [attrs for tag, attrs, _ in elements(html) if tag == "div" and "data-notice" in attrs], html


def test_cada_nivel_tiene_su_estilo_y_su_rol():
    notices, html = _notices([Message(constants.SUCCESS, "Listo."), Message(constants.ERROR, "No se pudo.")])

    assert [(n["class"], n["role"]) for n in notices] == [
        ("notice notice--success", "status"),
        ("notice notice--error", "alert"),
    ]
    assert "lucide-check" in html and "lucide-circle-alert" in html


def test_el_boton_de_cerrar_viene_oculto_para_que_sin_js_el_aviso_quede_visible():
    _, html = _notices([Message(constants.INFO, "Aviso.")])
    [close] = [attrs for tag, attrs, _ in elements(html) if tag == "button"]
    assert "hidden" in close and close["aria-label"] == "Cerrar aviso"


def test_iniciar_y_cerrar_sesion_no_dejan_aviso(client, make_shop, make_member):
    make_member("barbero@example.com", make_shop("a"), Role.BARBER)

    home = client.post(
        reverse("account_login"), {"login": "barbero@example.com", "password": TEST_PASSWORD}, follow=True
    )
    login_page = client.post(reverse("account_logout"), follow=True)

    for page in (home, login_page):
        assert "data-notice" not in page.content.decode()


def test_el_boton_de_cerrar_usa_el_icono_x_de_lucide():
    _, html = _notices([Message(constants.INFO, "Aviso.")])
    assert "lucide-x" in html
