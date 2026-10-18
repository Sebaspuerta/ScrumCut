import secrets
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from allauth.account.models import EmailAddress
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.cash import services as cash
from apps.catalog import services as catalog
from apps.clients import services as clients
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.inventory.models import Product, StockLevel
from apps.legal.models import LegalDocument
from apps.staff import services as staff
from apps.tenancy.branch_scope import ALL, BranchScope, resolve_scope
from apps.tenancy.models import Barbershop, Branch, Membership, MembershipBranch
from apps.tenancy.roles import Role

# Se genera en cada corrida: una contraseña literal en el código la marca gitleaks como secreto.
TEST_PASSWORD = secrets.token_urlsafe(18)


def scope_of(membership: Membership, branch: Branch | None = None, *, everything: bool = False) -> BranchScope:
    """El alcance de una membresía como lo arma el middleware (docs/sedes.md, fase S2).

    Con `branch`, esa sede; con `everything`, "todas"; sin nada, el valor por defecto del rol.
    Si lo pedido no está permitido, la prueba falla aquí en vez de seguir con otra sede.
    """
    requested = ALL if everything else (str(branch.public_id) if branch else None)
    scope = resolve_scope(membership, requested)
    assert requested is None or scope.token == requested, f"{membership.role} no puede usar {requested}"
    return scope


def stock_of(product: Product, branch: Branch | None = None) -> int:
    """Existencias del producto en `branch` o, sin ella, la suma de todas sus sedes."""
    levels = StockLevel.objects.filter(product=product)
    if branch is not None:
        levels = levels.filter(branch=branch)
    return levels.aggregate(total=Sum("quantity"))["total"] or 0


@pytest.fixture
def make_shop(db):
    def _make(slug: str) -> Barbershop:
        return Barbershop.objects.create(trade_name=f"Barbería {slug}", slug=slug)

    return _make


@pytest.fixture
def make_member(db):
    def _make(email: str, shop: Barbershop, role: Role, password: str = TEST_PASSWORD) -> User:
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
    branch = Branch.objects.get()  # la Sede principal de toda barbería nueva
    branch.name = "Centro"
    branch.save(update_fields=["name", "updated_at"])
    MembershipBranch.objects.create(membership=cashier, branch=branch)  # el cajero entra a Centro

    ana = staff.create_barber(
        owner,
        {"display_name": "Ana", "membership": ana_login.public_id},
        commission_type="percentage",
        commission_value=40,
    )
    beto = staff.create_barber(
        owner,
        {"display_name": "Beto", "membership": beto_login.public_id},
        commission_type="percentage",
        commission_value=50,
    )

    corte = catalog.create_service(owner, name="Corte", price=Decimal("25000"), duration_minutes=30)
    barba = catalog.create_service(owner, name="Barba", price=Decimal("15000"), duration_minutes=20)
    cuchilla = inventory.create_product(
        owner,
        {"name": "Cuchilla", "product_type": "consumible", "purchase_cost": Decimal("1000")},
        initial_stock=10,
        scope=scope_of(owner),
    )
    inventory.add_consumable(owner, corte.public_id, product=cuchilla.public_id, quantity=1)
    cera = inventory.create_product(
        owner,
        {"name": "Cera", "product_type": "venta", "purchase_cost": Decimal("8000"), "sale_price": Decimal("20000")},
        initial_stock=5,
        scope=scope_of(owner),
    )
    laura = clients.create_client(
        owner,
        {"full_name": "Laura Gómez", "phone": "3001234567"},
        data_consent_at=timezone.now(),
        data_policy_version="2026-10",
    )
    session = cash.open_session(cashier, scope_of(cashier, branch), opening_amount=Decimal("50000"))
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


def publish(kind: str, version: str, days_ago: int = 1) -> LegalDocument:
    """Documento de prueba: los textos reales los redacta y aprueba una persona, nunca una migración."""
    return LegalDocument.objects.create(
        kind=kind,
        version=version,
        body=f"Texto de prueba de {kind} {version}.",
        published_at=timezone.now() - timedelta(days=days_ago),
    )


@pytest.fixture
def legal_documents(db) -> dict[str, LegalDocument]:
    return {kind: publish(kind, "1.0") for kind in LegalDocument.Kind.values}
