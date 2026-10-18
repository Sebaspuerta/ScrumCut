import pytest

from apps.tenancy.roles import Role


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)
