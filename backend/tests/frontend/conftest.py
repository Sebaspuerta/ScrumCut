import pytest
from allauth.mfa.models import Authenticator
from django.urls import reverse

from apps.tenancy.roles import Role


@pytest.fixture
def owner_page(client, make_shop, make_member):
    """El inicio visto por el dueño. Sin 2FA el middleware lo enviaría a configurarlo."""
    owner = make_member("dueno@example.com", make_shop("a"), Role.OWNER)
    Authenticator.objects.create(user=owner, type=Authenticator.Type.TOTP, data={})
    client.force_login(owner)
    return client.get(reverse("home"))


@pytest.fixture
def barber_page(client, make_shop, make_member):
    client.force_login(make_member("barbero@example.com", make_shop("a"), Role.BARBER))
    return client.get(reverse("home"))
