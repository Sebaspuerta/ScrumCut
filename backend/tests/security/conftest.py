import pytest
from django.core.cache import cache
from django.urls import reverse

from tests.conftest import TEST_PASSWORD


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Los límites de allauth viven en la caché: sin limpiarla, una prueba heredaría los intentos de otra."""
    cache.clear()


def signup_data(email: str = "nueva@example.com", **overrides) -> dict:
    return {"email": email, "password1": TEST_PASSWORD, "password2": TEST_PASSWORD, "legal_consent": "on", **overrides}


def sign_up(client, **overrides):
    return client.post(reverse("account_signup"), signup_data(**overrides))
