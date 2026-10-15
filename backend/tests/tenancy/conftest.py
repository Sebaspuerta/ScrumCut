from decimal import Decimal

import pytest

from apps.cash import services as cash
from apps.tenancy import services as tenancy
from apps.tenancy.models import Barbershop


@pytest.fixture
def norte(world):
    """Segunda sede de `world` con su caja abierta, para cobrar allí lo que nació en Centro."""
    Barbershop.objects.filter(pk=world.shop.pk).update(max_branches=3)
    branch = tenancy.create_branch(world.owner, {"name": "Norte"})
    cash.open_session(world.cashier, branch.public_id, opening_amount=Decimal("0"))
    return branch
