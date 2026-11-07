"""Páginas de error de Django (fase R6): su código, sin secretos ni rastro técnico (S6) y con la CSP estricta."""

import re

import pytest
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import path, reverse

# Django busca los handlers en el urlconf de esta prueba.
from config.urls import handler400, handler403, handler404, handler500  # noqa: F401 — los usa Django, no el código
from config.urls import urlpatterns as project_urlpatterns
from tests.frontend.test_csp_markup import _assert_csp_friendly
from tests.security.test_secrets_exposure import _assert_no_secret

TECHNICAL_TRACE = re.compile(
    r"Traceback|Exception|Error:|File \"|line \d+|django|CSRF token|RuntimeError", re.IGNORECASE
)
SECRET_DETAIL = "detalle interno del fallo"


def fails(request):
    raise RuntimeError(SECRET_DETAIL)


def forbidden(request):
    raise PermissionDenied(SECRET_DETAIL)


urlpatterns = [path("prueba/falla/", fails), path("prueba/prohibido/", forbidden), *project_urlpatterns]


def _assert_clean_error_page(response, status: int, title: str) -> None:
    html = response.content.decode()
    assert response.status_code == status
    assert f"<h1>{title}</h1>" in html
    assert '<meta name="robots" content="noindex">' in html
    assert '<div class="error-page__logo">' in html
    assert SECRET_DETAIL not in html and not TECHNICAL_TRACE.search(html)
    assert "Content-Security-Policy" in response.headers
    _assert_csp_friendly(html)
    _assert_no_secret(html)


@pytest.mark.django_db
def test_la_404_dice_que_la_pagina_no_existe(client):
    _assert_clean_error_page(client.get("/no-existe/"), 404, "Esta página no existe")


@pytest.mark.django_db
@pytest.mark.urls("tests.frontend.test_error_pages")
def test_la_403_no_muestra_el_motivo_interno(client):
    _assert_clean_error_page(client.get("/prueba/prohibido/"), 403, "No tienes acceso a esta página")


@pytest.mark.django_db
def test_la_400_responde_a_un_host_no_permitido(client):
    _assert_clean_error_page(client.get("/salud/", HTTP_HOST="otro.example"), 400, "No pudimos entender la solicitud")


@pytest.mark.django_db
def test_el_fallo_de_csrf_pide_recargar_sin_decir_el_motivo(legal_documents):
    strict = Client(enforce_csrf_checks=True)
    response = strict.post(reverse("account_login"), {"login": "a@example.com", "password": "x"})
    _assert_clean_error_page(response, 403, "La página venció")


@pytest.mark.urls("tests.frontend.test_error_pages")
def test_la_500_se_muestra_aunque_falle_la_base_de_datos_y_da_el_contacto_de_soporte(settings):
    """Sin la marca django_db, pytest-django bloquea toda consulta: la página no puede depender de la base."""
    settings.SUPPORT_EMAIL = "soporte@example.test"
    response = Client(raise_request_exception=False).get("/prueba/falla/")

    _assert_clean_error_page(response, 500, "Algo salió mal de nuestro lado")
    assert (
        "Intenta de nuevo en unos minutos. Si sigue pasando, escríbenos a soporte@example.test."
        in response.content.decode()
    )


@pytest.mark.urls("tests.frontend.test_error_pages")
def test_la_500_sin_contacto_configurado_no_ofrece_escribir(settings):
    settings.SUPPORT_EMAIL = ""
    html = Client(raise_request_exception=False).get("/prueba/falla/").content.decode()

    assert "<p>Intenta de nuevo en unos minutos.</p>" in html and "escríbenos" not in html
