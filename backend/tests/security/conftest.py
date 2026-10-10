from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.legal.models import LegalDocument
from tests.conftest import TEST_PASSWORD


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Los límites de allauth viven en la caché: sin limpiarla, una prueba heredaría los intentos de otra."""
    cache.clear()


def publish(kind: str, version: str, days_ago: int = 1) -> LegalDocument:
    """Documento de prueba: los textos reales los redacta y aprueba una persona, nunca una migración."""
    return LegalDocument.objects.create(
        kind=kind,
        version=version,
        body=f"Texto de prueba de {kind} {version}.",
        published_at=timezone.now() - timedelta(days=days_ago),
    )


@pytest.fixture
def legal_documents(db) -> dict[str, LegalDocument]:
    return {kind: publish(kind, "1.0") for kind in LegalDocument.Kind.values}


def signup_data(email: str = "nueva@example.com", **overrides) -> dict:
    return {"email": email, "password1": TEST_PASSWORD, "password2": TEST_PASSWORD, "legal_consent": "on", **overrides}


def sign_up(client, **overrides):
    return client.post(reverse("account_signup"), signup_data(**overrides))
