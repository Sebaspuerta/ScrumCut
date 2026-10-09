"""Lecturas de comandas. Los managers ya filtran por la barbería activa.

El alcance del Barbero (solo sus comandas) vive aquí, en `scoped_orders`, y los
services lo usan también para bloquear: un Barbero no lee ni toca comandas ajenas
(defecto 6). Los reportes leen solo los valores copiados al cerrar (defecto 1).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied
from django.core.paginator import Page, Paginator
from django.db.models import Count, DecimalField, F, Prefetch, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.sales.models import ItemType, Order, OrderItem, OrderStatus
from apps.staff.models import Barber
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_member, ensure_permission
from apps.tenancy.roles import Role, role_has_permission

DELETED_SUFFIX = " (eliminado)"
_ZERO = Decimal("0.00")


def _money_sum(expression) -> Coalesce:
    return Coalesce(Sum(expression), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2))


def own_barber(membership: Membership) -> Barber | None:
    return Barber.objects.filter(membership=membership, deleted_at__isnull=True).first()


def scoped_orders(membership: Membership) -> QuerySet[Order]:
    """Comandas que esta membresía puede ver y operar.

    El Barbero ve las que creó y aquellas donde es el barbero principal. Sin JOIN,
    para poder usarse con `select_for_update`.
    """
    orders = Order.objects.all()
    if membership.role == Role.BARBER:
        mine = Q(created_by_id=membership.user_id)
        barber = own_barber(membership)
        if barber is not None:
            mine |= Q(barber=barber)
        orders = orders.filter(mine)
    return orders


def _day_bounds(tz_name: str, start: date, end: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    return datetime.combine(start, time.min, tz), datetime.combine(end + timedelta(days=1), time.min, tz)


def local_today(membership: Membership) -> date:
    return timezone.now().astimezone(ZoneInfo(membership.barbershop.timezone)).date()


def list_orders(
    membership: Membership,
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    barber: UUID | str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page:
    """Fechas de creación en la zona de la barbería, ambos extremos incluidos."""
    ensure_permission(membership, "comandas.ver")
    orders = scoped_orders(membership).select_related("client", "barber", "branch")
    if status:
        orders = orders.filter(status=status)
    if barber is not None:
        orders = orders.filter(barber__public_id=barber)
    tz_name = membership.barbershop.timezone
    if date_from is not None:
        orders = orders.filter(created_at__gte=_day_bounds(tz_name, date_from, date_from)[0])
    if date_to is not None:
        orders = orders.filter(created_at__lt=_day_bounds(tz_name, date_to, date_to)[1])
    return Paginator(orders.order_by("-number"), page_size).get_page(page)


def get_order(membership: Membership, public_id: UUID | str) -> Order:
    """Lanza `Order.DoesNotExist` si no existe o está fuera del alcance del rol."""
    ensure_permission(membership, "comandas.ver")
    items = OrderItem.objects.select_related("service", "product", "barber").order_by("pk")
    return (
        scoped_orders(membership)
        .select_related("client", "barber", "branch")
        .prefetch_related(Prefetch("items", queryset=items), "payments")
        .get(public_id=public_id)
    )


def item_display_name(item: OrderItem) -> str:
    """Regla 19: el nombre guardado en la venta, marcado si el servicio o producto se borró."""
    related = item.service if item.item_type == ItemType.SERVICE else item.product
    if related is not None and related.is_deleted:
        return item.name + DELETED_SUFFIX
    return item.name


def barber_display_name(barber: Barber | None) -> str | None:
    if barber is None:
        return None
    return barber.display_name + (DELETED_SUFFIX if barber.is_deleted else "")


def _closed_lines(barber: Barber, start: datetime, end: datetime) -> QuerySet[OrderItem]:
    return OrderItem.objects.filter(
        barber=barber,
        order__status=OrderStatus.CLOSED,
        order__closed_at__gte=start,
        order__closed_at__lt=end,
    )


def barber_performance(
    membership: Membership, barber: UUID | str, date_from: date | None = None, date_to: date | None = None
) -> dict:
    """Regla 44 con el defecto 1 corregido: suma solo lo copiado en las líneas al cerrar.

    Rango por defecto: los últimos 30 días en la zona de la barbería. Lo ve quien
    tiene `barberos.ver`, y cada barbero el suyo.
    """
    ensure_member(membership)
    target = Barber.objects.get(public_id=barber)
    if not role_has_permission(membership.role, "barberos.ver"):
        mine = own_barber(membership)
        if mine is None or mine.pk != target.pk:
            raise PermissionDenied
    date_to = date_to or local_today(membership)
    date_from = date_from or date_to - timedelta(days=30)
    start, end = _day_bounds(membership.barbershop.timezone, date_from, date_to)
    totals = _closed_lines(target, start, end).aggregate(
        orders_count=Count("order", distinct=True),
        services_count=Coalesce(Sum("quantity", filter=Q(item_type=ItemType.SERVICE)), 0),
        sales_total=_money_sum(F("line_total") - F("line_discount")),
        commission_total=_money_sum("commission_amount"),
    )
    return {"barber": target, "date_from": date_from, "date_to": date_to, **totals}


def my_cuts_today(membership: Membership) -> dict:
    """Regla 54: el barbero ve cuántos servicios hizo hoy, sin cifras de dinero."""
    ensure_member(membership)
    barber = own_barber(membership)
    if barber is None:
        return {"cuts_today": 0}
    today = local_today(membership)
    start, end = _day_bounds(membership.barbershop.timezone, today, today)
    cuts = (
        _closed_lines(barber, start, end)
        .filter(item_type=ItemType.SERVICE)
        .aggregate(total=Coalesce(Sum("quantity"), 0))["total"]
    )
    return {"cuts_today": cuts}
