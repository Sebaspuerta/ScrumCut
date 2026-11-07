"""Estado de acceso (fase R6): por qué la persona entra o no, solo con sus propias membresías."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.tenancy.models import Barbershop, Membership
from apps.tenancy.roles import Role
from apps.tenancy.selectors import Access, AccessState, access_state
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

SUPPORT = "soporte@scrumtech.example"


@pytest.fixture(autouse=True)
def support_email(settings):
    settings.SUPPORT_EMAIL = SUPPORT


def _state(user) -> AccessState:
    return access_state(user, None)


def _status(shop: Barbershop, status: Barbershop.Status) -> None:
    Barbershop.objects.filter(pk=shop.pk).update(status=status)


def test_sin_membresias_no_tiene_barberia():
    user = User.objects.create_user(email="sola@example.com", password=TEST_PASSWORD)
    assert _state(user) == AccessState(Access.NO_BARBERSHOP)


def test_con_la_membresia_retirada_dice_de_cual_barberia(make_shop, make_member):
    user = make_member("retirado@example.com", make_shop("a"), Role.CASHIER)
    Membership.objects.filter(user=user).update(is_active=False)
    assert _state(user) == AccessState(Access.MEMBERSHIP_INACTIVE, "Barbería a")


@pytest.mark.parametrize(
    ("status", "access"),
    [(Barbershop.Status.SUSPENDED, Access.BARBERSHOP_SUSPENDED), (Barbershop.Status.CLOSED, Access.BARBERSHOP_CLOSED)],
)
def test_la_barberia_bloqueada_da_el_contacto_de_soporte_solo_al_dueno(make_shop, make_member, status, access):
    shop = make_shop("a")
    owner = make_member("dueno@example.com", shop, Role.OWNER)
    cashier = make_member("caja@example.com", shop, Role.CASHIER)
    _status(shop, status)

    assert _state(owner) == AccessState(access, "Barbería a", SUPPORT)
    assert _state(cashier) == AccessState(access, "Barbería a")


def test_con_varias_barberias_no_nombra_ninguna_y_da_el_contacto_de_soporte(make_shop, make_member):
    user = make_member("doble@example.com", make_shop("a"), Role.CASHIER)
    Membership.objects.create(user=user, barbershop=make_shop("b"), role=Role.CASHIER)
    assert _state(user) == AccessState(Access.SEVERAL_BARBERSHOPS, support_email=SUPPORT)


def test_si_una_barberia_funciona_las_demas_no_se_mencionan(make_shop, make_member):
    user = make_member("mixta@example.com", make_shop("a"), Role.CASHIER)
    retired = Membership.objects.create(user=user, barbershop=make_shop("b"), role=Role.CASHIER, is_active=False)
    _status(retired.barbershop, Barbershop.Status.SUSPENDED)
    assert _state(user) == AccessState(Access.ACTIVE, "Barbería a")


def test_me_entrega_el_estado_sin_datos_de_la_otra_barberia(make_shop, make_member):
    user = make_member("suspendido@example.com", make_shop("a"), Role.CASHIER)
    other = make_shop("b")
    _status(Barbershop.objects.get(slug="a"), Barbershop.Status.SUSPENDED)
    client = Client()
    client.force_login(user)

    body = client.get(reverse("api_me")).json()

    assert body["access"] == {"status": "barbershop_suspended", "barbershop": "Barbería a", "support_email": None}
    assert (body["barbershop"], body["permissions"]) == (None, [])
    assert other.trade_name not in str(body)


def test_me_con_acceso_activo_nombra_su_barberia(make_shop, make_member):
    client = Client()
    client.force_login(make_member("caja@example.com", make_shop("a"), Role.CASHIER))
    access = client.get(reverse("api_me")).json()["access"]
    assert access == {"status": "active", "barbershop": "Barbería a", "support_email": None}
