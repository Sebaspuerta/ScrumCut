import pytest
from allauth.mfa.models import Authenticator
from django.test import Client
from django.urls import reverse

from apps.tenancy.roles import Role


def logged_in_with_mfa(user) -> Client:
    """Dueño o administrador con 2FA: sin él, el middleware lo enviaría a configurarlo."""
    Authenticator.objects.create(user=user, type=Authenticator.Type.TOTP, data={})
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def owner_page(make_shop, make_member):
    owner = make_member("dueno@example.com", make_shop("a"), Role.OWNER)
    return logged_in_with_mfa(owner).get(reverse("home"))


@pytest.fixture
def barber_page(client, make_shop, make_member):
    client.force_login(make_member("barbero@example.com", make_shop("a"), Role.BARBER))
    return client.get(reverse("home"))
