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
def owner_page(make_shop, make_member, built_app):
    """La página de la app de React para un dueño con 2FA."""
    owner = make_member("dueno@example.com", make_shop("a"), Role.OWNER)
    return logged_in_with_mfa(owner).get(reverse("react_app"))
