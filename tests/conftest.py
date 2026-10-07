from decimal import Decimal
from types import SimpleNamespace

import pytest
from allauth.account.models import EmailAddress
from django.utils import timezone

from apps.accounts.models import User
from apps.cash import services as cash
from apps.catalog import services as catalog
from apps.clients import services as clients
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.staff import services as staff
from apps.tenancy.models import Barbershop, Branch, Membership
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


@pytest.fixture
def world(member, in_shop):
    """Una barbería lista para vender.

    - Ana (40 %) y Beto (50 %), cada uno con su usuario Barbero.
    - Corte 25 000 que gasta 1 cuchilla (costo 1 000, stock 10); Barba 15 000.
    - Cera: venta 20 000, costo 8 000, stock 5. Cliente Laura.
    - Caja abierta en Centro con base de 50 000.
    """
    owner = member(Role.OWNER, in_shop)
    cashier = member(Role.CASHIER, in_shop)
    ana_login = member(Role.BARBER, in_shop, email="ana@a.test")
    beto_login = member(Role.BARBER, in_shop, email="beto@a.test")
    branch = Branch.objects.create(name="Centro")

    ana = staff.create_barber(owner, {"display_name": "Ana", "membership": ana_login.public_id}, "percentage", 40)
    beto = staff.create_barber(owner, {"display_name": "Beto", "membership": beto_login.public_id}, "percentage", 50)

    corte = catalog.create_service(owner, name="Corte", price=Decimal("25000"), duration_minutes=30)
    barba = catalog.create_service(owner, name="Barba", price=Decimal("15000"), duration_minutes=20)
    cuchilla = inventory.create_product(
        owner,
        {"name": "Cuchilla", "product_type": "consumible", "purchase_cost": Decimal("1000")},
        initial_stock=10,
    )
    inventory.add_consumable(owner, corte.public_id, cuchilla.public_id, 1)
    cera = inventory.create_product(
        owner,
        {"name": "Cera", "product_type": "venta", "purchase_cost": Decimal("8000"), "sale_price": Decimal("20000")},
        initial_stock=5,
    )
    laura = clients.create_client(
        owner,
        {"full_name": "Laura Gómez", "phone": "3001234567"},
        data_consent_at=timezone.now(),
        data_policy_version="2026-10",
    )
    session = cash.open_session(cashier, branch.public_id, Decimal("50000"))
    return SimpleNamespace(
        shop=in_shop,
        owner=owner,
        cashier=cashier,
        ana_login=ana_login,
        beto_login=beto_login,
        branch=branch,
        ana=ana,
        beto=beto,
        corte=corte,
        barba=barba,
        cuchilla=cuchilla,
        cera=cera,
        laura=laura,
        session=session,
    )
