"""Las páginas renderizadas cumplen la CSP estricta: sin estilos ni scripts en línea, sin almacenamiento local."""

import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

INLINE_STYLE = re.compile(r"\sstyle\s*=", re.IGNORECASE)
# Solo se permiten scripts con src.
INLINE_SCRIPT = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>", re.IGNORECASE)
INLINE_HANDLER = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
BROWSER_STORAGE = re.compile(r"localStorage|sessionStorage")


def _assert_csp_friendly(html: str) -> None:
    assert not INLINE_STYLE.search(html)
    assert not INLINE_SCRIPT.search(html)
    assert not INLINE_HANDLER.search(html)
    assert not BROWSER_STORAGE.search(html)


def test_la_app_con_sesion_cumple_la_csp(owner_page):
    assert owner_page.status_code == 200
    _assert_csp_friendly(owner_page.content.decode())


@pytest.mark.parametrize("url_name", ["account_login", "account_signup", "account_reset_password"])
def test_las_pantallas_de_cuenta_cumplen_la_csp(client, legal_documents, url_name):
    _assert_csp_friendly(client.get(reverse(url_name)).content.decode())
