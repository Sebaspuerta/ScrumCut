"""Punto 11: el servidor valida el formulario aunque el navegador no lo haga."""

import pytest

from apps.accounts.models import User
from tests.conftest import TEST_PASSWORD
from tests.security.conftest import sign_up

pytestmark = pytest.mark.django_db

COMMON_PASSWORD = "1q2w3e4r5t6y"  # gitleaks:allow — común a propósito: la prueba verifica que se rechaza


def _error_codes(response, field: str) -> set[str]:
    return {error.code for error in response.context["form"].errors.as_data().get(field, [])}


def test_el_registro_rechaza_un_correo_invalido(client, legal_documents):
    response = sign_up(client, email="esto-no-es-un-correo")
    assert response.status_code == 200 and _error_codes(response, "email") == {"invalid"}


def test_el_registro_rechaza_contrasenas_que_no_coinciden(client, legal_documents):
    response = sign_up(client, password2=TEST_PASSWORD + "-distinta")
    assert response.status_code == 200 and "password2" in response.context["form"].errors


def test_el_registro_rechaza_una_contrasena_comun(client, legal_documents):
    response = sign_up(client, password1=COMMON_PASSWORD, password2=COMMON_PASSWORD)
    assert response.status_code == 200 and "password_too_common" in _error_codes(response, "password1")
    assert not User.objects.exists()
