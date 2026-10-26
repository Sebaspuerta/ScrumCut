"""Lecturas de la pantalla de Comandas (fase F3): pestañas con su conteo, búsqueda, filtro y resumen del día.

Todo por el alcance de sede y por el alcance del rol (`scoped_orders`: el barbero ve solo las suyas).
Cada bloque es una consulta agregada o una lista con sus líneas precargadas: el número de consultas no
crece con el número de comandas.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.paginator import Page, Paginator
from django.db.models import Count, DecimalField, F, Prefetch, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from apps.cash.choices import PaymentMethod
from apps.sales.models import EDITABLE_STATUSES, Order, OrderItem, OrderStatus, Payment
from apps.sales.selectors import day_bounds, local_today, scoped_orders
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

OPEN, CLOSED_TODAY, CANCELLED_TODAY = "abiertas", "cerradas", "anuladas"
TABS = ((OPEN, "Abiertas"), (CLOSED_TODAY, "Cerradas hoy"), (CANCELLED_TODAY, "Anuladas"))
PAGE_SIZE = 50
WALK_IN = "Cliente de mostrador"
_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BoardFilter:
    tab: str = OPEN
    search: str = ""
    barber: UUID | None = None
    day: date | None = None  # el día de las cerradas y las anuladas; sin día, hoy


def _bounds(membership: Membership, day: date | None) -> tuple[datetime, datetime]:
    """El día pedido (o hoy) en la zona de la barbería."""
    day = day or local_today(membership)
    return day_bounds(membership.barbershop.timezone, day, day)


def _tab_conditions(membership: Membership, day: date | None = None) -> dict[str, Q]:
    """Las abiertas son todas las vigentes; las cerradas y las anuladas, las del día."""
    start, end = _bounds(membership, day)
    return {
        OPEN: Q(status__in=EDITABLE_STATUSES),
        CLOSED_TODAY: Q(status=OrderStatus.CLOSED, closed_at__gte=start, closed_at__lt=end),
        CANCELLED_TODAY: Q(status=OrderStatus.CANCELLED, cancelled_at__gte=start, cancelled_at__lt=end),
    }


def _visible(membership: Membership, scope: BranchScope) -> QuerySet[Order]:
    ensure_permission(membership, "comandas.ver")
    return scope.readable(membership, scoped_orders(membership))


def tab_counts(membership: Membership, *, scope: BranchScope, day: date | None = None) -> dict[str, int]:
    """Cuántas comandas hay en cada pestaña, en una sola consulta."""
    conditions = _tab_conditions(membership, day)
    return _visible(membership, scope).aggregate(**{tab: Count("pk", filter=q) for tab, q in conditions.items()})


def _search(orders: QuerySet[Order], term: str) -> QuerySet[Order]:
    """Por número (#147 o 147) o por el nombre del cliente."""
    term = term.strip().lstrip("#")
    if not term:
        return orders
    by_name = Q(client__full_name__icontains=term)
    return orders.filter(by_name | Q(number=int(term))) if term.isdigit() else orders.filter(by_name)


def _lines() -> Prefetch:
    return Prefetch("items", queryset=OrderItem.objects.select_related("barber").order_by("pk"))


def board_orders(membership: Membership, *, scope: BranchScope, filters: BoardFilter, page: int = 1) -> Page:
    """Las comandas de la pestaña, con sus líneas, barberos y pagos ya cargados."""
    orders = _visible(membership, scope).filter(_tab_conditions(membership, filters.day)[filters.tab])
    orders = _search(orders, filters.search)
    if filters.barber is not None:
        orders = orders.filter(Q(barber__public_id=filters.barber) | Q(items__barber__public_id=filters.barber))
    orders = (
        orders.distinct()
        .select_related("client", "barber", "cancelled_by")
        .prefetch_related(_lines(), "payments")
        .order_by("-number")
    )
    return Paginator(orders, PAGE_SIZE).get_page(page)


def _money(expression, condition: Q | None = None) -> Coalesce:
    return Coalesce(
        Sum(expression, filter=condition), Value(_ZERO), output_field=DecimalField(max_digits=14, decimal_places=2)
    )


def closed_today_summary(membership: Membership, *, scope: BranchScope, day: date | None = None) -> dict[str, Decimal]:
    """Lo cobrado en el día (hoy, si no se indica) en efectivo y en otros medios, y lo que quedó como fiado."""
    closed = _visible(membership, scope).filter(_tab_conditions(membership, day)[CLOSED_TODAY])
    paid = Payment.objects.filter(order__in=closed).aggregate(
        cash=_money("amount", Q(method=PaymentMethod.CASH)),
        other=_money("amount", ~Q(method=PaymentMethod.CASH)),
    )
    credit = closed.aggregate(credit=_money(F("total") - F("amount_paid")))["credit"]
    return {**paid, "credit": credit}


def _short(name: str) -> str:
    """Julián Restrepo → Julián R."""
    first, *rest = name.split()
    return f"{first} {rest[0][0]}." if rest else first


def _barbers(order: Order) -> str:
    names = dict.fromkeys(_short(line.barber.display_name) for line in order.items.all() if line.barber_id)
    if not names and order.barber_id:
        names = {_short(order.barber.display_name): None}
    return ", ".join(names) or "Sin barbero"


def _payment_label(order: Order) -> str:
    methods = dict.fromkeys(PaymentMethod(payment.method).label for payment in order.payments.all())
    if order.balance > 0:
        methods["Fiado"] = None
    return " + ".join(methods) or "Sin cobro"


def board_row(order: Order) -> dict:
    """Lo que muestra una fila de la lista, con las líneas y los pagos ya precargados (sin consultas)."""
    return {
        "order": order,
        "client": order.client.full_name if order.client_id else WALK_IN,
        "barbers": _barbers(order),
        "items": ", ".join(line.name for line in order.items.all()),
        "payment": _payment_label(order),
    }
