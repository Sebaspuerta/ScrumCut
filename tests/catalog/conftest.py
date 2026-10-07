import pytest

from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Membership


@pytest.fixture
def shop(make_shop):
    return make_shop("a")


@pytest.fixture
def other_shop(make_shop):
    return make_shop("b")


@pytest.fixture
def in_shop(shop):
    with tenant_context(shop.pk):
        yield shop


@pytest.fixture
def member(make_member):
    def _member(role: str, shop) -> Membership:
        user = make_member(f"{role}@{shop.slug}.test", shop, role)
        return Membership.objects.get(user=user, barbershop=shop)

    return _member
