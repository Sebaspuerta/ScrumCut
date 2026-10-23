"""La entrada (login, registro, recuperar contraseña, 2FA) tiene sus propios estilos (`entrance__*`, `auth-*`).

Protege contra lo que rompió el login en F3: una clase genérica de las pantallas internas (`.field`)
coincidió con la del contenedor de cada campo de la entrada y le puso una caja alrededor. Ninguna
clase de la entrada puede estar definida en el CSS de las pantallas internas.
"""

import re

import pytest
from django.conf import settings
from django.urls import reverse

from tests.frontend.html_support import elements

pytestmark = pytest.mark.django_db

CSS = settings.FRONTEND_DIR / "static/css"
# Compartidos a propósito con la entrada: los botones y los avisos de error.
SHARED = {"components/buttons.css", "components/states.css", "components/fields.css", "modules/login.css"}
CLASS = re.compile(r"\.([a-zA-Z][\w-]*)")
ENTRANCE_PAGES = ["account_login", "account_signup", "account_reset_password"]


def _internal_classes() -> set[str]:
    """Las clases que define el CSS de las pantallas internas (marco, componentes y módulos)."""
    found = set()
    for path in CSS.rglob("*.css"):
        if path.relative_to(CSS).as_posix() in SHARED or path.name == "tokens.css":
            continue
        css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        found |= {name for name in CLASS.findall(css) if not name[0].isdigit()}
    return found


def _classes(html: str) -> set[str]:
    return {name for _, attrs, _ in elements(html) for name in (attrs.get("class") or "").split()}


@pytest.mark.parametrize("url_name", ENTRANCE_PAGES)
def test_la_entrada_no_usa_clases_de_las_pantallas_internas(client, legal_documents, url_name):
    html = client.get(reverse(url_name)).content.decode()
    assert _classes(html) & _internal_classes() == set()


def test_cada_campo_del_login_es_un_solo_campo_sin_la_clase_generica(client, legal_documents):
    html = client.get(reverse("account_login")).content.decode()
    classes = _classes(html)
    assert "field" not in classes  # la de los controles de las pantallas internas
    assert "auth-field" in classes


def test_el_css_de_la_entrada_solo_usa_sus_propias_clases():
    css = re.sub(r"/\*.*?\*/", "", (CSS / "modules/login.css").read_text(encoding="utf-8"), flags=re.DOTALL)
    selectors = {name for name in CLASS.findall(css) if not name[0].isdigit()}
    foreign = {name for name in selectors if not name.startswith(("entrance", "auth-", "logo3d", "button", "notices"))}
    assert foreign == set()
