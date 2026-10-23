import pytest
from django.core.cache import cache
from django.test import Client

from tests.frontend.conftest import logged_in_with_mfa
from tests.tenancy.conftest import norte  # noqa: F401  (fixture: segunda sede de `world`)


@pytest.fixture(autouse=True)
def _fresh_throttle():
    """Los límites de la API viven en la caché: sin limpiarla, una prueba heredaría las peticiones de otra."""
    cache.clear()


@pytest.fixture
def owner_client(world) -> Client:
    return logged_in_with_mfa(world.owner.user)


@pytest.fixture
def cashier_client(world) -> Client:
    """El cajero de `world` solo entra a Centro."""
    client = Client()
    client.force_login(world.cashier.user)
    return client
