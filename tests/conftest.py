import pytest
from allauth.account.models import EmailAddress

from apps.accounts.models import User
from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Barbershop, Membership
from apps.tenancy.roles import Role


@pytest.fixture
def make_shop(db):
    def _make(slug: str) -> Barbershop:
        return Barbershop.objects.create(trade_name=f"Barbería {slug}", slug=slug)

    return _make


@pytest.fixture
def make_member(db):
    def _make(email: str, shop: Barbershop, role: Role, password: str = "clave-larga-de-prueba-2026") -> User:
        user = User.objects.create_user(email=email, password=password)
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        Membership.objects.create(user=user, barbershop=shop, role=role)
        return user

    return _make


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
    """Membresía con un rol en una barbería. `email` permite varias del mismo rol."""

    def _member(role: Role, shop: Barbershop, email: str | None = None) -> Membership:
        user = make_member(email or f"{role}@{shop.slug}.test", shop, role)
        return Membership.objects.get(user=user, barbershop=shop)

    return _member
