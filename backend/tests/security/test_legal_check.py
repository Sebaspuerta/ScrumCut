"""Punto 13: el chequeo de despliegue falla si faltan los documentos que abren el registro."""

from io import StringIO

import pytest
from django.core.checks import run_checks
from django.core.management import CommandError, call_command

from apps.legal.models import LegalDocument

pytestmark = pytest.mark.django_db


def _legal_errors(**kwargs) -> list[str]:
    return [message.id for message in run_checks(tags=["legal"], **kwargs)]


def test_el_chequeo_falla_sin_documentos_publicados():
    assert _legal_errors(include_deployment_checks=True) == ["legal.E001"]


def test_el_chequeo_pasa_con_los_documentos_publicados(legal_documents):
    assert _legal_errors(include_deployment_checks=True) == []


def test_un_borrador_sin_publicar_no_cuenta(legal_documents):
    LegalDocument.objects.filter(kind=LegalDocument.Kind.PRIVACY_NOTICE).update(published_at=None)
    assert _legal_errors(include_deployment_checks=True) == ["legal.E001"]


def test_el_chequeo_no_corre_fuera_del_despliegue():
    assert _legal_errors() == []


def test_el_comando_de_ci_se_niega_a_correr_fuera_de_ci(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(CommandError):
        call_command("publicar_documentos_ci")
    assert not LegalDocument.objects.exists()


def test_el_comando_de_ci_publica_lo_que_pide_el_chequeo(monkeypatch):
    monkeypatch.setenv("CI", "true")
    call_command("publicar_documentos_ci", stdout=StringIO())
    call_command("publicar_documentos_ci", stdout=StringIO())  # idempotente

    assert LegalDocument.objects.count() == 3
    assert _legal_errors(include_deployment_checks=True) == []
