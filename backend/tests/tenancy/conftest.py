from decimal import Decimal

import pytest

from apps.cash import services as cash
from apps.inventory import services as inventory
from apps.tenancy import services as tenancy
from apps.tenancy.models import Barbershop
from tests.conftest import scope_of


@pytest.fixture
def norte(world):
    """Segunda sede de `world`, con su caja abierta por el dueño: el cajero de `world` es solo de Centro.

    Ana y Beto trabajan en las dos sedes, así que se pueden elegir en las comandas de Norte.
    Norte tiene su propio stock (fase S4b): 3 ceras y 4 cuchillas.
    """
    Barbershop.objects.filter(pk=world.shop.pk).update(max_branches=3)
    branch = tenancy.create_branch(world.owner, {"name": "Norte"})
    for barber in (world.ana, world.beto):
        tenancy.set_barber_branches(world.owner, barber.public_id, branches=[world.branch.public_id, branch.public_id])
    cash.open_session(world.owner, scope_of(world.owner, branch), opening_amount=Decimal("0"))
    for product, quantity in ((world.cera, 3), (world.cuchilla, 4)):
        inventory.register_entry(
            world.owner, product.public_id, scope=scope_of(world.owner, branch), quantity=quantity, reason="Compra"
        )
    return branch
