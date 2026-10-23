"""La página de la app de React (/app/): con sesión, el HTML con los archivos del manifest de Vite y nada en línea."""

import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from apps.core.vite_manifest import read_entry
from tests.frontend.test_csp_markup import _assert_csp_friendly

pytestmark = pytest.mark.django_db

MANIFEST = {
    "src/main.tsx": {"file": "assets/main-abc.js", "isEntry": True, "css": ["assets/main-abc.css"], "imports": ["_v"]},
    "_v": {"file": "assets/vendor-def.js", "css": ["assets/vendor-def.css"]},
}


@pytest.fixture
def built_app(tmp_path, settings):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    settings.REACT_APP_MANIFEST = manifest
    return manifest


def test_el_lector_devuelve_el_script_y_los_estilos_de_lo_que_importa_primero(built_app):
    entry = read_entry(built_app, "src/main.tsx")

    assert entry.script == "/static/app/assets/main-abc.js"
    assert entry.styles == ("/static/app/assets/vendor-def.css", "/static/app/assets/main-abc.css")


def test_sin_compilar_falla_con_un_mensaje_claro(tmp_path):
    with pytest.raises(ImproperlyConfigured, match="npm run build"):
        read_entry(tmp_path / "manifest.json", "src/main.tsx")


@pytest.mark.parametrize("path", ["/app/", "/app/agenda/hoy"])
def test_con_sesion_entrega_la_pagina_con_los_archivos_compilados(client, world, built_app, path):
    client.force_login(world.cashier.user)

    html = client.get(path).content.decode()

    assert '<script type="module" src="/static/app/assets/main-abc.js"></script>' in html
    assert '<link rel="stylesheet" href="/static/app/assets/main-abc.css">' in html
    assert '<meta name="robots" content="noindex">' in html
    _assert_csp_friendly(html)


def test_sin_sesion_manda_al_login(client, built_app):
    response = client.get(reverse("react_app"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))
