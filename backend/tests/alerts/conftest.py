import pytest

from apps.tenancy.models import Branch, MembershipBranch
from apps.tenancy.roles import Role


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)


@pytest.fixture
def cashier(member, in_shop):
    """Cajero de la Sede principal: sin sede asignada no tendría alcance (fase S2)."""
    membership = member(Role.CASHIER, in_shop)
    MembershipBranch.objects.create(membership=membership, branch=Branch.objects.order_by("pk").first())
    return membership
