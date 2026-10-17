from decimal import Decimal

import pytest

from apps.cash import services as cash
from apps.tenancy import services as tenancy
from apps.tenancy.models import Barbershop
from tests.conftest import scope_of


@pytest.fixture
def norte(world):
    """Segunda sede de `world`, con su caja abierta por el dueño: el cajero de `world` es solo de Centro."""
    Barbershop.objects.filter(pk=world.shop.pk).update(max_branches=3)
    branch = tenancy.create_branch(world.owner, {"name": "Norte"})
    cash.open_session(world.owner, scope_of(world.owner, branch), opening_amount=Decimal("0"))
    return branch
