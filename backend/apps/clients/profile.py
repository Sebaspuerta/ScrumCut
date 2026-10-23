"""Ficha de un cliente en la pantalla de Clientes (fase F4), siempre en las sedes del alcance.

El nivel sale de `client_profile` (regla 47 con los umbrales de la barbería) y el progreso usa esos
mismos umbrales. Cada bloque es una consulta agregada o una lista corta: el número de consultas no
crece con el número de visitas.
"""

from decimal import Decimal
from uuid import UUID

from django.db.models import Count, Prefetch, QuerySet, Sum

from apps.clients.board import active_here
from apps.clients.models import Client
from apps.clients.selectors import ClientStatus, client_profile
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.sales.models import ItemType, Order, OrderItem, OrderStatus
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import BarbershopSettings, Membership

LAST_VISITS = 5


def level_progress(visits: int, settings: BarbershopSettings) -> dict:
    """Cuántas visitas faltan para el siguiente nivel por visitas: Nuevo → Frecuente → VIP."""
    steps = ((settings.frequent_min_visits, ClientStatus.FREQUENT), (settings.vip_min_visits, ClientStatus.VIP))
    for target, level in steps:
        if visits < target:
            return {"next": level.label, "missing": target - visits, "percent": min(100, visits * 100 // target)}
    return {"next": None, "missing": 0, "percent": 100}


def _visits(scope: BranchScope, client) -> QuerySet[Order]:
    return scope.apply(Order.objects.filter(client=client, status=OrderStatus.CLOSED))


def _favorites(scope: BranchScope, client) -> dict:
    """El barbero con más visitas y el servicio que más pide, en las sedes del alcance."""
    lines = OrderItem.objects.filter(order__in=_visits(scope, client))
    barber = (
        lines.filter(barber__isnull=False)
        .values("barber__display_name")
        .annotate(visits=Count("order", distinct=True))
        .order_by("-visits", "barber__display_name")
        .first()
    )
    service = (
        lines.filter(item_type=ItemType.SERVICE)
        .values("name")
        .annotate(times=Sum("quantity"))
        .order_by("-times", "name")
        .first()
    )
    return {"barber": barber, "service": service}


def _last_visits(scope: BranchScope, client) -> list[Order]:
    items = OrderItem.objects.select_related("barber").order_by("pk")
    visits = _visits(scope, client).prefetch_related(Prefetch("items", queryset=items), "payments")
    return list(visits.order_by("-closed_at")[:LAST_VISITS])


def _open_debt(scope: BranchScope, client) -> Receivable | None:
    """El fiado vivo más antiguo del cliente en las sedes del alcance, para enlazarlo."""
    debts = scope.apply(
        Receivable.objects.filter(client=client, status__in=OPEN_STATUSES, balance__gt=0), "origin_branch"
    )
    return debts.order_by("created_at").first()


def client_card(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> dict:
    """La ficha: nivel con su progreso, ticket, gasto, barbero habitual, deuda y últimas visitas."""
    profile = client_profile(membership, public_id, scope=scope)
    client = profile["client"]
    here = Client.objects.filter(pk=client.pk).annotate(here=active_here(scope)).values_list("here", flat=True).get()
    if not here:
        # Sin historial en esta sede: solo la identidad, nunca nada de otra sede.
        return {"client": client, "has_activity": False}
    visits = profile["visits"]
    return {
        **profile,
        "has_activity": True,
        "progress": level_progress(visits, BarbershopSettings.objects.get()),
        "ticket": profile["spent"] / visits if visits else Decimal("0.00"),
        **_favorites(scope, client),
        "last_visits": _last_visits(scope, client),
        "open_debt": _open_debt(scope, client),
    }
