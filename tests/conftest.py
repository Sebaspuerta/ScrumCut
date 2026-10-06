import pytest
from allauth.account.models import EmailAddress

from apps.accounts.models import User
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
