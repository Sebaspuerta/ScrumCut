"""Solo desarrollo: una barbería de ejemplo con 30 días de ventas, cajas, barberos, productos y alertas."""

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
from apps.tenancy.models import Barbershop, Branch, Membership
from apps.tenancy.roles import Role

SLUG = "demo"
OWNER_EMAIL = "demo-dueno@scrumcut.test"
# Comandas por día de la semana (lunes a sábado); el domingo la barbería no abre.
DAILY_ORDERS = (6, 7, 7, 8, 12, 13)
OPENING_HOUR = 8
FIRST_SALE_HOUR = 9
LAST_SALE_HOUR = 19
METHODS = ("efectivo", "efectivo", "nequi", "tarjeta")
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
        shop = Barbershop.objects.create(trade_name="Barbería Demo", slug=SLUG)
        today = timezone.localdate()
        with tenant_context(shop.pk), at(_moment(today - timedelta(days=options["dias"]), 7)):
            # Desde el primer día: las comisiones vigentes y el stock inicial anteceden a las ventas.
            world = _build_catalog(shop, password, today)
        with tenant_context(shop.pk):
            _build_history(world, options["dias"], random.Random(2026))  # noqa: S311 — datos de ejemplo
            generate_alerts(timezone.localdate())
        self.stdout.write(f"Barbería de ejemplo lista. Entra con {OWNER_EMAIL} y la contraseña {password}")


def _owner(shop: Barbershop, password: str) -> Membership:
    user = User.objects.create_user(email=OWNER_EMAIL, password=password, full_name="Dueño Demo")
    EmailAddress.objects.create(user=user, email=OWNER_EMAIL, verified=True, primary=True)
    return Membership.objects.create(user=user, barbershop=shop, role=Role.OWNER)


def _product(owner, name: str, cost: str, price: str, stock: int, **extra):
    data = {"name": name, "product_type": "venta", "purchase_cost": D(cost), "sale_price": D(price), **extra}
    return inventory.create_product(owner, data, initial_stock=stock)


def _build_catalog(shop: Barbershop, password: str, today: date) -> SimpleNamespace:
    owner = _owner(shop, password)
    branch = Branch.objects.create(name="Principal")
    barbers = [
        staff.create_barber(owner, {"display_name": name}, "percentage", rate)
        for name, rate in (("Julián R.", 40), ("Camilo O.", 40), ("Santiago P.", 35))
    ]
    services = [
        catalog.create_service(owner, name=name, price=D(price), duration_minutes=minutes)
        for name, price, minutes in (("Corte", "25000", 30), ("Barba", "15000", 20), ("Corte y barba", "35000", 45))
    ]
    blade = inventory.create_product(
        owner, {"name": "Cuchilla", "product_type": "consumible", "purchase_cost": D("1000")}, initial_stock=900
    )
    inventory.add_consumable(owner, services[0].public_id, blade.public_id, 1)
    products = [
        _product(owner, "Cera mate", "11000", "25000", 400),
        _product(owner, "Aceite para barba", "18000", "35000", 40, minimum_stock=30),
        _product(owner, "Shampoo anticaída", "17000", "30000", 60),
    ]
    _product(owner, "Tónico capilar", "12000", "28000", 5, expiration_date=today + timedelta(days=12))
    return SimpleNamespace(owner=owner, branch=branch, barbers=barbers, services=services, products=products)


def _moment(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), ZoneInfo(settings.TIME_ZONE))


def _sell(world: SimpleNamespace, rng: random.Random) -> None:
    item = {"product": rng.choice(world.products).public_id} if rng.random() < 0.25 else {}
    sales.quick_register(
        world.owner,
        world.branch.public_id,
        rng.choice(world.barbers).public_id,
        rng.choice(METHODS),
        service=None if item else rng.choice(world.services).public_id,
        **item,
    )


def _open_day(world: SimpleNamespace, day: date) -> CashSession:
    with at(_moment(day, OPENING_HOUR)):
        session = cash.open_session(world.owner, world.branch.public_id, D("200000"))
    # La base se registra con la hora real de la apertura simulada.
    CashSession.objects.filter(pk=session.pk).update(opened_at=_moment(day, OPENING_HOUR))
    return session


def _sale_times(day: date, until: datetime, rng: random.Random) -> list[datetime]:
    """Horas de las comandas del día sin pasar de `until`; si el día va por la mitad, la parte que le toca."""
    first, last = _moment(day, FIRST_SALE_HOUR), min(_moment(day, LAST_SALE_HOUR), until)
    if last <= first:
        return []
    minutes = int((last - first).total_seconds() // 60)
    share = minutes / ((LAST_SALE_HOUR - FIRST_SALE_HOUR) * 60)
    count = round(DAILY_ORDERS[day.weekday()] * share)
    return sorted(first + timedelta(minutes=rng.randint(0, minutes)) for _ in range(count))


def _sell_day(world: SimpleNamespace, day: date, until: datetime, rng: random.Random) -> None:
    for moment in _sale_times(day, until, rng):
        with at(moment):
            _sell(world, rng)


def _close_day(world: SimpleNamespace, session: CashSession, day: date, rng: random.Random) -> None:
    with at(_moment(day, 20)):
        cash.register_manual_movement(
            world.owner,
            session.public_id,
            kind="gasto",
            amount=D("15000"),
            payment_method="efectivo",
            description="Aseo",
        )
        counted = expected_cash(session) + D(rng.choice((0, 0, 0, -2000, 5000)))
        cash.close_session(world.owner, session.public_id, counted)


def _build_history(world: SimpleNamespace, days: int, rng: random.Random) -> None:
    today = timezone.localdate()
    for offset in range(days - 1, 0, -1):
        day = today - timedelta(days=offset)
        if day.weekday() == 6:  # domingo: cerrado
            continue
        session = _open_day(world, day)
        _sell_day(world, day, _moment(day, LAST_SALE_HOUR), rng)
        _close_day(world, session, day, rng)
    _build_today(world, today, rng)
    _overdue_debt(world.owner, today)


def _build_today(world: SimpleNamespace, today: date, rng: random.Random) -> None:
    """Hoy solo pasa lo que ya pudo pasar: la caja abre a su hora y las ventas llegan hasta ahora."""
    now = timezone.localtime()  # TIME_ZONE es America/Bogota, la zona de la barbería de ejemplo
    if today.weekday() == 6 or now < _moment(today, OPENING_HOUR):
        return
    _open_day(world, today)
    _sell_day(world, today, now, rng)


def _overdue_debt(owner: Membership, today: date) -> None:
    client = clients.create_client(
        owner, {"full_name": "Cliente de ejemplo"}, data_consent_at=timezone.now(), data_policy_version="demo"
    )
    receivables.create_manual(owner, client.public_id, D("180000"), due_date=today - timedelta(days=7))
