"""Punto 13: el registro exige la autorización de datos y deja evidencia de la versión aceptada."""

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.legal.models import Acceptance, LegalDocument
from tests.security.conftest import publish, sign_up

pytestmark = pytest.mark.django_db

Kind = LegalDocument.Kind


def test_sin_la_casilla_no_hay_registro(client, legal_documents):
    response = sign_up(client, legal_consent="")
    assert "legal_consent" in response.context["form"].errors
    assert not User.objects.exists()


def test_la_casilla_enlaza_a_los_documentos_vigentes(client, legal_documents):
    page = client.get(reverse("account_signup")).content.decode()
    for slug in ("tratamiento-de-datos", "terminos", "privacidad"):
        assert reverse("legal_document", args=[slug]) in page


def test_al_registrarse_quedan_las_dos_aceptaciones_con_version_ip_y_fecha(client, legal_documents):
    sign_up(client)

    user = User.objects.get(email="nueva@example.com")
    accepted = {a.document.kind: a for a in Acceptance.objects.filter(user=user).select_related("document")}
    assert set(accepted) == {Kind.TERMS, Kind.DATA_POLICY}
    assert {a.document for a in accepted.values()} == {legal_documents[Kind.TERMS], legal_documents[Kind.DATA_POLICY]}
    assert all(a.ip_address == "127.0.0.1" and a.accepted_at for a in accepted.values())


def test_se_acepta_la_version_publicada_mas_reciente(client, legal_documents):
    newer = publish(Kind.TERMS, "2.0", days_ago=0)
    publish(Kind.TERMS, "3.0", days_ago=-5)  # programada: todavía no rige
    sign_up(client)
    assert Acceptance.objects.get(document__kind=Kind.TERMS).document == newer


def test_si_falla_la_aceptacion_no_queda_el_usuario(client, legal_documents, monkeypatch):
    def broken(user, request):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr("apps.accounts.forms.accept_signup_documents", broken)
    with pytest.raises(RuntimeError):
        sign_up(client)
    assert not User.objects.exists()


@pytest.mark.parametrize("missing", [Kind.TERMS, Kind.DATA_POLICY, Kind.PRIVACY_NOTICE])
def test_sin_un_documento_publicado_el_registro_esta_cerrado(client, legal_documents, missing):
    legal_documents[missing].delete()
    sign_up(client)
    assert not User.objects.exists()
    assert "account/signup_closed.html" in [t.name for t in client.get(reverse("account_signup")).templates]


def test_los_documentos_se_leen_en_texto_plano(client, legal_documents):
    response = client.get(reverse("legal_document", args=["cookies"]))
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode() == legal_documents[Kind.COOKIES].body
    assert client.get(reverse("legal_document", args=["inexistente"])).status_code == 404
