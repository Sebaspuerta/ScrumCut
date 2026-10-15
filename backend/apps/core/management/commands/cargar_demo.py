"""Solo desarrollo: una barbería de ejemplo con dos sedes, 30 días de ventas, cajas, barberos y alertas."""

import random
import secrets
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock
from zoneinfo import ZoneInfo

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.alerts.services import generate_alerts
from apps.cash import services as cash
from apps.cash.models import CashSession
from apps.cash.selectors import expected_cash
from apps.catalog import services as catalog
from apps.clients import services as clients
from apps.core.tenant_context import tenant_context
from apps.inventory import services as inventory
from apps.receivables import services as receivables
from apps.sales import services as sales
from apps.staff import services as staff
from apps.tenancy import services as tenancy
from apps.tenancy.models import Barbershop, Branch, Membership
from apps.tenancy.roles import Role

SLUG = "demo"
OWNER_EMAIL = "demo-dueno@scrumcut.test"
CASHIER_EMAIL = "demo-cajero@scrumcut.test"
MAX_BRANCHES = 3
# Comandas por día de la semana (lunes a sábado) en Centro; el domingo no se abre. Norte vende la mitad.
DAILY_ORDERS = (6, 7, 7, 8, 12, 13)
BRANCH_TRAFFIC = {"Centro": 1.0, "Norte": 0.5}
OPENING_HOUR = 8
FIRST_SALE_HOUR = 9
LAST_SALE_HOUR = 19
CLOSING_HOUR = 20
METHODS = ("efectivo", "efectivo", "nequi", "tarjeta")
DEBT_TOTAL = Decimal("180000")
DEBT_PAYMENT = Decimal("60000")
D = Decimal


@contextmanager
def at(moment: datetime):
    """Los services fechan con timezone.now(); para crear días pasados se fija esa hora mientras tanto."""
    with mock.patch("django.utils.timezone.now", return_value=moment):
        yield


class Command(BaseCommand):
    help = "Solo desarrollo: crea la barbería de ejemplo 'demo' con datos para ver el tablero."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dias", type=int, default=30, help="Días de ventas hacia atrás, contando hoy.")

    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError("cargar_demo solo corre en desarrollo (DEBUG activo); nunca en producción.")
        if Barbershop.objects.filter(slug=SLUG).exists():
            raise CommandError(f"La barbería de ejemplo '{SLUG}' ya existe.")
        password = secrets.token_urlsafe(12)
        shop = Barbershop.objects.create(trade_name="Barbería Demo", slug=SLUG, max_branches=MAX_BRANCHES)
        today = timezone.localdate()
        with tenant_context(shop.pk), at(_moment(today - timedelta(days=options["dias"]), 7)):
            # Desde el primer día: las comisiones vigentes, el stock inicial y el fiado anteceden a las ventas.
            world = _build_world(shop, password, today)
        with tenant_context(shop.pk):
            _build_history(world, options["dias"], random.Random(2026))  # noqa: S311 — datos de ejemplo
            generate_alerts(timezone.localdate())
        self.stdout.write(
            f"Barbería de ejemplo lista. Entra con {OWNER_EMAIL} (dueño) o {CASHIER_EMAIL} (cajero de Centro) "
            f"y la contraseña {password}"
        )


# ── Barbería, sedes y personal ───────────────────────────────────────────────


def _person(shop: Barbershop, email: str, name: str, password: str, role: Role) -> Membership:
    user = User.objects.create_user(email=email, password=password, full_name=name)
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return Membership.objects.create(user=user, barbershop=shop, role=role)


def _branches(owner: Membership) -> dict[str, Branch]:
    """La Sede principal de toda barbería nueva pasa a llamarse Centro; Norte es la segunda."""
    centro = tenancy.update_branch(owner, Branch.objects.get().public_id, data={"name": "Centro", "city": "Bogotá"})
    norte = tenancy.create_branch(owner, {"name": "Norte", "city": "Bogotá"})
    return {"Centro": centro, "Norte": norte}


def _barbers(owner: Membership, branches: dict[str, Branch]) -> dict[str, list]:
    """Julián en Centro, Camilo en Norte y Santiago en las dos."""
    team = {}
    for name, rate, works_in in (
        ("Julián R.", 40, ("Centro",)),
        ("Camilo O.", 40, ("Norte",)),
        ("Santiago P.", 35, ("Centro", "Norte")),
    ):
        barber = staff.create_barber(
            owner,
            {"display_name": name},
            commission_type="percentage",
            commission_value=rate,
            branches=[branches[branch].public_id for branch in works_in],
        )
        team[name] = (barber, works_in)
    return {branch: [barber for barber, works_in in team.values() if branch in works_in] for branch in branches}


def _product(owner, name: str, cost: str, price: str, stock: int, **extra):
    data = {"name": name, "product_type": "venta", "purchase_cost": D(cost), "sale_price": D(price), **extra}
    return inventory.create_product(owner, data, initial_stock=stock)


def _catalog(owner: Membership, today: date) -> SimpleNamespace:
    services = [
        catalog.create_service(owner, name=name, price=D(price), duration_minutes=minutes)
        for name, price, minutes in (("Corte", "25000", 30), ("Barba", "15000", 20), ("Corte y barba", "35000", 45))
    ]
    blade = inventory.create_product(
        owner, {"name": "Cuchilla", "product_type": "consumible", "purchase_cost": D("1000")}, initial_stock=1500
    )
    inventory.add_consumable(owner, services[0].public_id, product=blade.public_id, quantity=1)
    products = [
        _product(owner, "Cera mate", "11000", "25000", 400),
        _product(owner, "Aceite para barba", "18000", "35000", 55, minimum_stock=30),
        _product(owner, "Shampoo anticaída", "17000", "30000", 60),
    ]
    _product(owner, "Tónico capilar", "12000", "28000", 5, expiration_date=today + timedelta(days=12))
    return SimpleNamespace(services=services, products=products)


def _manual_debt(owner: Membership, centro: Branch, today: date):
    """Un fiado manual de Centro, vencido hace una semana; se abona en parte en su caja (decisión 3)."""
    client = clients.create_client(
        owner, {"full_name": "Cliente de ejemplo"}, data_consent_at=timezone.now(), data_policy_version="demo"
    )
    return receivables.create_manual(
        owner, client.public_id, total=DEBT_TOTAL, branch=centro.public_id, due_date=today - timedelta(days=7)
    )


def _build_world(shop: Barbershop, password: str, today: date) -> SimpleNamespace:
    owner = _person(shop, OWNER_EMAIL, "Dueño Demo", password, Role.OWNER)
    branches = _branches(owner)
    cashier = _person(shop, CASHIER_EMAIL, "Cajero Demo", password, Role.CASHIER)
    tenancy.set_cashier_branches(owner, cashier.public_id, branches=[branches["Centro"].public_id])
    return SimpleNamespace(
        owner=owner,
        branches=branches,
        barbers=_barbers(owner, branches),
        catalog=_catalog(owner, today),
        debt=_manual_debt(owner, branches["Centro"], today),
    )


# ── Días de venta ────────────────────────────────────────────────────────────


def _moment(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), ZoneInfo(settings.TIME_ZONE))


def _sell(world: SimpleNamespace, branch: str, rng: random.Random) -> None:
    item = {"product": rng.choice(world.catalog.products).public_id} if rng.random() < 0.25 else {}
    sales.quick_register(
        world.owner,
        world.branches[branch].public_id,
        barber=rng.choice(world.barbers[branch]).public_id,
        method=rng.choice(METHODS),
        service=None if item else rng.choice(world.catalog.services).public_id,
        **item,
    )


def _open_day(world: SimpleNamespace, branch: str, day: date) -> CashSession:
    with at(_moment(day, OPENING_HOUR)):
        session = cash.open_session(world.owner, world.branches[branch].public_id, opening_amount=D("200000"))
    # La base se registra con la hora real de la apertura simulada.
    CashSession.objects.filter(pk=session.pk).update(opened_at=_moment(day, OPENING_HOUR))
    return session


def _sale_times(day: date, until: datetime, orders: float, rng: random.Random) -> list[datetime]:
    """Horas de las comandas del día sin pasar de `until`; si el día va por la mitad, la parte que le toca."""
    first, last = _moment(day, FIRST_SALE_HOUR), min(_moment(day, LAST_SALE_HOUR), until)
    if last <= first:
        return []
    minutes = int((last - first).total_seconds() // 60)
    share = minutes / ((LAST_SALE_HOUR - FIRST_SALE_HOUR) * 60)
    return sorted(first + timedelta(minutes=rng.randint(0, minutes)) for _ in range(round(orders * share)))


def _sell_day(world: SimpleNamespace, branch: str, day: date, until: datetime, rng: random.Random) -> None:
    orders = DAILY_ORDERS[day.weekday()] * BRANCH_TRAFFIC[branch]
    for moment in _sale_times(day, until, orders, rng):
        with at(moment):
            _sell(world, branch, rng)


def _close_day(world: SimpleNamespace, session: CashSession, day: date, rng: random.Random) -> None:
    with at(_moment(day, CLOSING_HOUR)):
        cash.register_manual_movement(
            world.owner,
            session.public_id,
            kind="gasto",
            amount=D("15000"),
            payment_method="efectivo",
            description="Aseo",
        )
        counted = expected_cash(session) + D(rng.choice((0, 0, 0, -2000, 5000)))
        cash.close_session(world.owner, session.public_id, counted_amount=counted)


def _pay_debt(world: SimpleNamespace, day: date) -> None:
    """Un fiado se abona solo en su sede de origen: el de ejemplo es de Centro."""
    with at(_moment(day, LAST_SALE_HOUR)):
        receivables.add_payment(
            world.owner,
            world.debt.public_id,
            amount=DEBT_PAYMENT,
            method="efectivo",
            branch=world.debt.origin_branch.public_id,
        )


def _past_day(world: SimpleNamespace, day: date, rng: random.Random, *, pay_debt: bool) -> None:
    for branch in world.branches:
        session = _open_day(world, branch, day)
        _sell_day(world, branch, day, _moment(day, LAST_SALE_HOUR), rng)
        if pay_debt and world.branches[branch] == world.debt.origin_branch:
            _pay_debt(world, day)
        _close_day(world, session, day, rng)


def _build_history(world: SimpleNamespace, days: int, rng: random.Random) -> None:
    today = timezone.localdate()
    working_days = [
        today - timedelta(days=offset)
        for offset in range(days - 1, 0, -1)
        if (today - timedelta(days=offset)).weekday() != 6
    ]
    for day in working_days:
        _past_day(world, day, rng, pay_debt=day == working_days[-1])
    _build_today(world, today, rng)


def _build_today(world: SimpleNamespace, today: date, rng: random.Random) -> None:
    """Hoy solo pasa lo que ya pudo pasar: las cajas abren a su hora y las ventas llegan hasta ahora."""
    now = timezone.localtime()  # TIME_ZONE es America/Bogota, la zona de la barbería de ejemplo
    if today.weekday() == 6 or now < _moment(today, OPENING_HOUR):
        return
    for branch in world.branches:
        _open_day(world, branch, today)
        _sell_day(world, branch, today, now, rng)
