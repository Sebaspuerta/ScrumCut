"""Lecturas de la pantalla de Clientes (fase F4): cifras de la sede, lista con nivel, filtros y orden.

La persona es de la barbería; visitas, gasto, deuda y nivel son de las sedes del alcance (decisiones 15
y 16 de docs/sedes.md). Cada cifra de la lista es una subconsulta correlacionada en la misma consulta,
así que el número de consultas no crece con el número de clientes ni de visitas.

`level_expression` es la regla de `client_status` escrita en SQL para poder filtrar y contar por nivel en
la base; tests/clients/test_client_levels.py comprueba que las dos dan lo mismo en cada umbral.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.paginator import Page, Paginator
from django.db.models import (
    Case,
    Count,
    DateTimeField,
    DecimalField,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Lower

from apps.clients.models import Client
from apps.clients.normalization import normalize_document
from apps.clients.selectors import ClientStatus
from apps.core import crypto
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.sales.models import Order, OrderStatus
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import BarbershopSettings, Membership
from apps.tenancy.permissions import ensure_permission

PAGE_SIZE = 50
NO_ACTIVITY = "sin_sede"  # nivel de la lista para un cliente encontrado por búsqueda sin actividad aquí
RECENT_DAYS = 90
ORDERINGS = {
    "ultima": (F("last_visit").desc(nulls_last=True), Lower("full_name")),
    "visitas": ("-visits", Lower("full_name")),
    "gasto": ("-spent_recent", Lower("full_name")),
    "deuda": ("-debt", Lower("full_name")),
}
_MONEY = DecimalField(max_digits=14, decimal_places=2)
_ZERO = Value(Decimal("0.00"))


@dataclass(frozen=True)
class ClientFilter:
    search: str = ""
    level: str = ""
    order: str = "ultima"


def _closed_orders(scope: BranchScope) -> QuerySet[Order]:
    return scope.apply(Order.objects.filter(client=OuterRef("pk"), status=OrderStatus.CLOSED))


def _per_client(queryset: QuerySet, expression, output) -> Subquery:
    return Subquery(queryset.values("client").annotate(value=expression).values("value")[:1], output_field=output)


def with_figures(clients: QuerySet[Client], scope: BranchScope, *, now: datetime) -> QuerySet[Client]:
    """Visitas, gasto (total y de 90 días), última visita y deuda en las sedes del alcance."""
    orders = _closed_orders(scope)
    recent = orders.filter(closed_at__gte=now - timedelta(days=RECENT_DAYS))
    debts = scope.apply(Receivable.objects.filter(client=OuterRef("pk"), status__in=OPEN_STATUSES), "origin_branch")
    return clients.annotate(
        visits=Coalesce(_per_client(orders, Count("pk"), IntegerField()), 0),
        spent=Coalesce(_per_client(orders, Sum("total"), _MONEY), _ZERO),
        spent_recent=Coalesce(_per_client(recent, Sum("total"), _MONEY), _ZERO),
        last_visit=_per_client(orders, Max("closed_at"), DateTimeField()),
        debt=Coalesce(_per_client(debts, Sum("balance"), _MONEY), _ZERO),
    )


def active_here(scope: BranchScope) -> Exists:
    """Si el cliente tiene actividad en las sedes del alcance: comandas (en cualquier estado) o fiados.

    Client no guarda en qué sede se registró, así que el registro no cuenta como actividad.
    """
    orders = scope.apply(Order.objects.filter(client=OuterRef("pk")))
    debts = scope.apply(Receivable.objects.filter(client=OuterRef("pk")), "origin_branch")
    return Exists(orders) | Exists(debts)


def level_expression(settings: BarbershopSettings, *, now: datetime) -> Case:
    """La regla de `client_status` (regla 47), en el mismo orden, sobre las cifras de `with_figures`."""
    inactive_before = now - timedelta(days=settings.inactive_after_days)
    return Case(
        When(debt__gt=0, then=Value(ClientStatus.DEBTOR)),
        When(last_visit__lt=inactive_before, then=Value(ClientStatus.INACTIVE)),
        When(visits=0, then=Value(ClientStatus.NEW)),
        When(
            Q(spent__gte=settings.vip_min_spent) | Q(visits__gte=settings.vip_min_visits), then=Value(ClientStatus.VIP)
        ),
        When(visits__gte=settings.frequent_min_visits, then=Value(ClientStatus.FREQUENT)),
        default=Value(ClientStatus.NEW),
    )


def _search(clients: QuerySet[Client], term: str) -> QuerySet[Client]:
    """Por nombre, por celular (los dígitos, con o sin espacios) o por cédula exacta (su huella)."""
    term = term.strip()
    if not term:
        return clients
    matches = Q(full_name__icontains=term) | Q(document_hash=crypto.keyed_hash(normalize_document(term)))
    digits = re.sub(r"\D", "", term)
    if len(digits) >= 3:  # menos de 3 dígitos coincidiría con casi cualquier celular
        matches |= Q(phone__contains=digits)
    return clients.filter(matches)


def client_rows(
    membership: Membership, *, scope: BranchScope, filters: ClientFilter, now: datetime, page: int = 1
) -> tuple[Page, dict]:
    """La página de clientes y el conteo por nivel (para los filtros).

    Sin búsqueda, solo los clientes con actividad en las sedes del alcance. La búsqueda encuentra a
    cualquier cliente de la barbería (la persona es común); uno sin actividad aquí sale con el nivel
    "Sin visitas en la sede" y sin cifras: las de otras sedes nunca se cuentan.
    """
    ensure_permission(membership, "clientes.ver")
    scope.check(membership)
    settings = BarbershopSettings.objects.get()
    clients = Client.objects.filter(deleted_at__isnull=True, anonymized_at__isnull=True)
    clients = _search(clients, filters.search).annotate(here=active_here(scope))
    if not filters.search.strip():
        # Sin búsqueda, la lista es la de la sede: solo quien tiene actividad en ella.
        clients = clients.filter(here=True)
    clients = with_figures(clients, scope, now=now)
    clients = clients.annotate(
        level=Case(When(here=False, then=Value(NO_ACTIVITY)), default=level_expression(settings, now=now))
    )
    counts = dict(clients.order_by().values_list("level").annotate(total=Count("pk")))
    if filters.level:
        clients = clients.filter(level=filters.level)
    ordered = clients.order_by(*ORDERINGS.get(filters.order, ORDERINGS["ultima"]))
    return Paginator(ordered, PAGE_SIZE).get_page(page), counts


# ── Cifras de arriba ─────────────────────────────────────────────────────────

RETURN_WINDOW = timedelta(days=30)
# Cohorte de "vuelven en 30 días": primera visita entre hace 120 y hace 30 días, así cada cliente tuvo
# sus 30 días completos para volver.
COHORT_START, COHORT_END = timedelta(days=120), RETURN_WINDOW


def _active(scope: BranchScope, now: datetime) -> dict:
    orders = scope.apply(Order.objects.filter(status=OrderStatus.CLOSED))
    recent = Q(closed_at__gte=now - timedelta(days=RECENT_DAYS))
    return orders.aggregate(
        active=Count("client", distinct=True, filter=recent), with_visits=Count("client", distinct=True)
    )


def _new(scope: BranchScope, month_start: datetime, previous_start: datetime) -> dict:
    """Clientes cuya primera visita en las sedes del alcance cayó en este mes y en el anterior."""
    firsts = scope.apply(Order.objects.filter(status=OrderStatus.CLOSED, client__isnull=False))
    firsts = firsts.values("client").annotate(first=Min("closed_at"))
    return firsts.aggregate(
        this_month=Count("client", filter=Q(first__gte=month_start)),
        last_month=Count("client", filter=Q(first__gte=previous_start, first__lt=month_start)),
    )


def _returning(scope: BranchScope, now: datetime) -> dict:
    """De los clientes de la cohorte, cuántos volvieron dentro de los 30 días siguientes a su primera visita."""
    first = _per_client(_closed_orders(scope), Min("closed_at"), DateTimeField())
    window_end = ExpressionWrapper(OuterRef("first") + Value(RETURN_WINDOW), output_field=DateTimeField())
    again = scope.apply(
        Order.objects.filter(
            client=OuterRef("pk"), status=OrderStatus.CLOSED, closed_at__gt=OuterRef("first"), closed_at__lte=window_end
        )
    )
    cohort = Client.objects.annotate(first=first).filter(first__gte=now - COHORT_START, first__lt=now - COHORT_END)
    # Dos conteos: dentro de un aggregate, Django no puede usar la anotación "first" en la subconsulta.
    return {"cohort": cohort.count(), "returned": cohort.filter(Exists(again)).count()}


def _debtors(scope: BranchScope) -> dict:
    debts = scope.apply(Receivable.objects.filter(status__in=OPEN_STATUSES, balance__gt=0), "origin_branch")
    return debts.aggregate(clients=Count("client", distinct=True), total=Coalesce(Sum("balance"), _ZERO))


def client_stats(membership: Membership, *, scope: BranchScope, now: datetime, month_start: datetime) -> dict:
    """Las cuatro cifras de arriba, cada una en una consulta agregada."""
    ensure_permission(membership, "clientes.ver")
    previous_start = (month_start - timedelta(days=1)).replace(day=1)
    returning = _returning(scope, now)
    rate = round(returning["returned"] * 100 / returning["cohort"]) if returning["cohort"] else None
    return {
        **_active(scope, now),
        **_new(scope, month_start, previous_start),
        "return_rate": rate,
        "debtors": _debtors(scope),
    }
