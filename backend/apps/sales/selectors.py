"""Lecturas de comandas. Los managers ya filtran por la barbería activa.

El alcance del Barbero (solo sus comandas) vive aquí, en `scoped_orders`, y los
services lo usan también para bloquear: un Barbero no lee ni toca comandas ajenas
(defecto 6). Los reportes leen solo los valores copiados al cerrar (defecto 1).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Page, Paginator
from django.db.models import Count, DecimalField, F, Prefetch, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.sales.models import ItemType, Order, OrderItem, OrderStatus
from apps.staff.models import Barber
from apps.staff.selectors import barbers_in_scope
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_member, ensure_permission
from apps.tenancy.roles import Role, role_has_permission

DELETED_SUFFIX = " (eliminado)"
DEFAULT_PERIOD_DAYS = 30
MY_CUTS_PAGE_SIZE = 20
NET_SALE = F("line_total") - F("line_discount")  # la venta de una línea, después de su parte del descuento
_ZERO = Decimal("0.00")


def _money_sum(expression, condition: Q | None = None) -> Coalesce:
    return Coalesce(
        Sum(expression, filter=condition), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2)
    )


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


def day_bounds(tz_name: str, start: date, end: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    return datetime.combine(start, time.min, tz), datetime.combine(end + timedelta(days=1), time.min, tz)


def local_today(membership: Membership) -> date:
    return timezone.now().astimezone(ZoneInfo(membership.barbershop.timezone)).date()


def month_start(membership: Membership) -> datetime:
    """El primer instante del mes en curso, en la zona de la barbería."""
    today = local_today(membership)
    return day_bounds(membership.barbershop.timezone, today.replace(day=1), today)[0]


def period_dates(
    membership: Membership, date_from: date | None = None, date_to: date | None = None
) -> tuple[date, date]:
    """Ambos extremos incluidos. Por defecto, los últimos 30 días contando hoy (regla 49)."""
    date_to = date_to or local_today(membership)
    date_from = date_from or date_to - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
    if date_from > date_to:
        raise ValidationError("La fecha inicial no puede ser posterior a la final.", code="invalid_period")
    return date_from, date_to


def list_orders(
    membership: Membership,
    *,
    scope: BranchScope,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    barber: UUID | str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page:
    """Las comandas de la sede del alcance. Fechas de creación en la zona de la barbería, ambos extremos incluidos."""
    ensure_permission(membership, "comandas.ver")
    scope.check(membership)
    orders = scope.apply(scoped_orders(membership)).select_related("client", "barber", "branch")
    if status:
        orders = orders.filter(status=status)
    if barber is not None:
        orders = orders.filter(barber__public_id=barber)
    tz_name = membership.barbershop.timezone
    if date_from is not None:
        orders = orders.filter(created_at__gte=day_bounds(tz_name, date_from, date_from)[0])
    if date_to is not None:
        orders = orders.filter(created_at__lt=day_bounds(tz_name, date_to, date_to)[1])
    return Paginator(orders.order_by("-number"), page_size).get_page(page)


def get_order(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> Order:
    """Lanza `Order.DoesNotExist` si no existe o está fuera del alcance del rol o de la sede."""
    ensure_permission(membership, "comandas.ver")
    scope.check(membership)
    items = OrderItem.objects.select_related("service", "product", "barber").order_by("pk")
    return (
        scope.apply(scoped_orders(membership))
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
    membership: Membership,
    barber: UUID | str,
    date_from: date | None = None,
    date_to: date | None = None,
    *,
    scope: BranchScope,
) -> dict:
    """Regla 44 con el defecto 1 corregido: suma solo lo copiado en las líneas al cerrar.

    Rango por defecto: el de `period_dates`, en la zona de la barbería. Lo ve quien
    tiene `barberos.ver`, y cada barbero el suyo. Solo las comandas de la sede del alcance.
    """
    ensure_member(membership)
    target = barbers_in_scope(membership, scope).get(public_id=barber)
    if not role_has_permission(membership.role, "barberos.ver"):
        mine = own_barber(membership)
        if mine is None or mine.pk != target.pk:
            raise PermissionDenied
    date_from, date_to = period_dates(membership, date_from, date_to)
    totals = _production(membership, target, date_from, date_to, scope=scope)
    return {"barber": target, "date_from": date_from, "date_to": date_to, **totals}


def _production(membership: Membership, barber: Barber, date_from: date, date_to: date, *, scope: BranchScope) -> dict:
    """Una sola consulta: comandas, servicios, venta neta y comisión copiada de las líneas del barbero."""
    start, end = day_bounds(membership.barbershop.timezone, date_from, date_to)
    return scope.apply(_closed_lines(barber, start, end), "order__branch").aggregate(
        orders_count=Count("order", distinct=True),
        services_count=Coalesce(Sum("quantity", filter=Q(item_type=ItemType.SERVICE)), 0),
        sales_total=_money_sum(NET_SALE),
        commission_total=_money_sum("commission_amount"),
    )


def _my_orders(barber: Barber, lines: QuerySet[OrderItem]) -> QuerySet[Order]:
    """Las comandas de esas líneas, cada una con solo lo del barbero: sus líneas, su venta y su comisión."""
    mine = Q(items__barber=barber)
    own_lines = OrderItem.objects.filter(barber=barber).select_related("service", "product").order_by("pk")
    return (
        Order.objects.filter(pk__in=lines.values("order"))
        .annotate(
            my_services=Coalesce(Sum("items__quantity", filter=mine & Q(items__item_type=ItemType.SERVICE)), 0),
            my_sales=_money_sum(F("items__line_total") - F("items__line_discount"), mine),
            my_commission=_money_sum("items__commission_amount", mine),
        )
        .prefetch_related(Prefetch("items", queryset=own_lines, to_attr="my_lines"))
        .order_by("-closed_at", "-number")
    )


def my_cuts(membership: Membership, *, scope: BranchScope, day: date | None = None, page: int = 1) -> dict:
    """«Mis cortes»: el barbero de la sesión, nunca otro, en la sede del alcance. Hoy, el mes en curso y una
    página de sus comandas cerradas del día (por defecto, hoy). Todo sale de lo copiado al cerrar cada línea.

    Sin un barbero propio (un cajero, un consultor), todo en cero y sin comandas.
    """
    ensure_permission(membership, "comandas.ver")
    scope.check(membership)
    today = local_today(membership)
    day = day or today
    barber = own_barber(membership)
    if barber is None:
        empty = {"orders_count": 0, "services_count": 0, "sales_total": _ZERO, "commission_total": _ZERO}
        orders = Order.objects.none()
        return {"barber": None, "day": day, "today": empty, "month": empty, "orders": _page(orders, page)}
    start, end = day_bounds(membership.barbershop.timezone, day, day)
    lines = scope.apply(_closed_lines(barber, start, end), "order__branch")
    return {
        "barber": barber,
        "day": day,
        "today": _production(membership, barber, today, today, scope=scope),
        "month": _production(membership, barber, today.replace(day=1), today, scope=scope),
        "orders": _page(_my_orders(barber, lines), page),
    }


def _page(orders: QuerySet[Order], page: int) -> Page:
    return Paginator(orders, MY_CUTS_PAGE_SIZE).get_page(page)
