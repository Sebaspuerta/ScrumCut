"""Menú de la cuenta y panel del asistente de la plantilla base."""

import pytest
from django.urls import reverse

from tests.frontend.html_support import elements, forms, inside

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("url_name", ["account_logout", "logout_everywhere"])
def test_los_cierres_de_sesion_son_post_con_csrf(owner_page, url_name):
    [form] = [form for form in forms(owner_page.content.decode()) if form["action"] == reverse(url_name)]
    assert form["method"] == "post"
    assert "csrfmiddlewaretoken" in form["fields"]


def test_los_cierres_de_sesion_estan_en_el_details_sin_depender_de_js(owner_page):
    html = owner_page.content.decode()
    actions = {form["action"] for form in inside(html, "menu-cuenta", "form")}
    [account] = [
        attrs for tag, attrs, _ in elements(html) if tag == "summary" and attrs.get("aria-controls") == "menu-cuenta"
    ]

    assert actions == {reverse("account_logout"), reverse("logout_everywhere")}
    assert account["aria-expanded"] == "false"  # menus.js lo mantiene al día al abrir y cerrar
    # Nada que lo esconda hasta que cargue el JavaScript: al abrir el <details> se ve igual.
    assert not [attrs for attrs in inside(html, "menu-cuenta", "div") if "hidden" in attrs]


def test_el_asistente_no_tiene_funcionalidad(owner_page):
    page = owner_page.content.decode()
    controls = inside(page, "assistant-panel", "input") + inside(page, "assistant-panel", "button")
    disabled = [control for control in controls if "aria-label" not in control]  # todo menos el botón de cerrar

    assert "El asistente estará disponible pronto." in page
    assert len(disabled) == 2 and all("disabled" in control for control in disabled)
    assert inside(page, "assistant-panel", "form") == []  # nada que se envíe al servidor


def test_el_nombre_completo_de_la_cuenta_queda_en_title_aunque_se_corte(owner_page):
    html = owner_page.content.decode()
    [summary] = [
        attrs for tag, attrs, _ in elements(html) if tag == "summary" and attrs.get("aria-controls") == "menu-cuenta"
    ]
    assert summary["title"] == "dueno@example.com · Dueño"
    assert summary["aria-label"] == "Cuenta de dueno@example.com, Dueño"


def test_el_asistente_se_cierra_con_el_icono_x_de_lucide(owner_page):
    [close] = [
        attrs for attrs in inside(owner_page.content.decode(), "assistant-panel", "button") if "aria-label" in attrs
    ]
    assert close["aria-label"] == "Cerrar asistente"
    assert "lucide-x" in owner_page.content.decode().split('id="assistant-panel"')[1]
