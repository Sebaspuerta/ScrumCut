"""Clientes en la app de React: lo mismo que leen las pantallas de Django (`clients.board`, `clients.profile`), en JSON.

La persona es de la barbería; visitas, gasto, deuda y nivel son de las sedes del alcance (decisiones 15 y 16 de
docs/sedes.md). El celular sale siempre enmascarado y el documento nunca sale: no hay un permiso para verlos
completos. El correo solo va a quien puede editar al cliente, para el formulario.
"""

from datetime import datetime
from uuid import UUID

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.api.receivables import receivable_row
from apps.clients.board import NO_ACTIVITY, ClientFilter, client_rows, client_stats
from apps.clients.forms import ORDER_LABELS, level_chips
from apps.clients.models import Client
from apps.clients.profile import client_card
from apps.clients.services import DUPLICATE_CLIENT, POSSIBLE_DUPLICATE
from apps.core.formatting import mask_phone
from apps.core.shell_menus import initials
from apps.core.templatetags.formatting import level_label
from apps.legal.models import LegalDocument
from apps.legal.selectors import current_document
from apps.legal.views import DOCUMENT_SLUGS
from apps.receivables.selectors import list_receivables
from apps.sales.models import Order
from apps.sales.selectors import barber_display_name, local_today, month_start
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import role_has_permission

ALL_BRANCHES_LEVEL = "Varía por sede"
CREDIT_SALE = "Fiado"  # una visita sin pagos quedó entera como fiado
CLIENT_RECEIVABLES = 5  # como las últimas visitas de la ficha
DATA_POLICY_SLUG = next(slug for slug, kind in DOCUMENT_SLUGS.items() if kind == LegalDocument.Kind.DATA_POLICY)


def data_policy() -> dict | None:
    """La política de tratamiento de datos vigente que el cliente autoriza al registrarse; sin ella, no se registra."""
    policy = current_document(LegalDocument.Kind.DATA_POLICY)
    if policy is None:
        return None
    return {"version": policy.version, "url": reverse("legal_document", args=[DATA_POLICY_SLUG])}


def _level(client: Client, scope: BranchScope) -> tuple[str | None, str]:
    """El nivel en la sede; en "todas", cada sede tiene el suyo; sin visitas aquí, ninguno."""
    if client.level == NO_ACTIVITY:
        return None, level_label(NO_ACTIVITY)
    if scope.is_all:
        return None, ALL_BRANCHES_LEVEL
    return client.level, level_label(client.level)


def client_row(client: Client, scope: BranchScope) -> dict:
    """Un cliente de la lista. Sin actividad en la sede (encontrado por búsqueda), sin cifras: las de otras sedes
    nunca se cuentan."""
    level, label = _level(client, scope)
    active = client.level != NO_ACTIVITY
    return {
        "id": client.public_id,
        "name": client.full_name,
        "phone": mask_phone(client.phone) or None,
        "has_activity": active,
        "level": level,
        "level_label": label,
        "visits": client.visits if active else None,
        "last_visit": client.last_visit if active else None,
        "spent_recent": client.spent_recent if active else None,
        "debt": client.debt if active else None,
    }


def _stats(membership: Membership, scope: BranchScope, now: datetime) -> dict:
    stats = client_stats(membership, scope=scope, now=now, month_start=month_start(membership))
    return {
        "active": stats["active"],
        "with_visits": stats["with_visits"],
        "new_this_month": stats["this_month"],
        "new_last_month": stats["last_month"],
        "return_rate": stats["return_rate"],
        "debtors": stats["debtors"]["clients"],
        "debt_total": stats["debtors"]["total"],
    }


def client_list(membership: Membership, *, scope: BranchScope, filters: ClientFilter, page: int) -> dict:
    """Las cuatro cifras de la sede, los filtros por nivel con su conteo y una página de clientes."""
    now = timezone.now()
    rows, counts = client_rows(membership, scope=scope, filters=filters, now=now, page=page)
    return {
        "search": filters.search,
        "level": filters.level,
        "order": filters.order,
        "levels": [
            {"value": chip["value"], "label": chip["label"], "count": chip["count"]}
            for chip in level_chips(counts, filters.level)
        ],
        "orderings": [{"value": value, "label": label} for value, label in ORDER_LABELS],
        "stats": _stats(membership, scope, now),
        "count": rows.paginator.count,
        "page": rows.number,
        "pages": rows.paginator.num_pages,
        "page_size": rows.paginator.per_page,
        "results": [client_row(client, scope) for client in rows],
        "data_policy": data_policy(),
    }


def _visit(order: Order) -> dict:
    lines = list(order.items.all())
    methods = [payment.get_method_display() for payment in order.payments.all()]
    return {
        "id": order.public_id,
        "closed_at": order.closed_at,
        "items": ", ".join(line.name for line in lines),
        "barber": barber_display_name(lines[0].barber) if lines else None,
        "methods": " · ".join(methods) or CREDIT_SALE,
        "total": order.total,
    }


def _activity(card: dict, scope: BranchScope) -> dict:
    """Nivel con su progreso, ticket, gasto, barbero habitual, lo que más pide, deuda y últimas visitas."""
    barber, service, debt = card["barber"], card["service"], card["open_debt"]
    status = card["status"]
    return {
        "level": None if scope.is_all else status.value,
        "level_label": ALL_BRANCHES_LEVEL if scope.is_all else status.label,
        "progress": card["progress"],
        "visits": card["visits"],
        "spent": card["spent"],
        "ticket": card["ticket"],
        "barber": {"name": barber["barber__display_name"], "visits": barber["visits"]} if barber else None,
        "favorite": service["name"] if service else None,
        "balance": card["balance"],
        "open_debt": debt.public_id if debt else None,
        "last_visits": [_visit(order) for order in card["last_visits"]],
    }


def _receivables(membership: Membership, client: Client, scope: BranchScope) -> list[dict] | None:
    """Sus últimos fiados en las sedes del alcance; sin fiados.ver, ninguno."""
    if not role_has_permission(membership.role, "fiados.ver"):
        return None
    receivables = list_receivables(membership, scope=scope, client=client.public_id).select_related("origin_branch")
    today = local_today(membership)
    return [receivable_row(receivable, today) for receivable in receivables[:CLIENT_RECEIVABLES]]


def _actions(membership: Membership, client: Client, scope: BranchScope) -> dict[str, bool]:
    role = membership.role
    return {
        "edit": not client.is_anonymized and role_has_permission(role, "clientes.editar"),
        "new_order": scope.branch is not None and role_has_permission(role, "comandas.crear"),
    }


def client_detail(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> dict:
    """La ficha. Sin historial en la sede, solo la identidad: nunca nada de otra sede."""
    card = client_card(membership, public_id, scope=scope)
    client = card["client"]
    actions = _actions(membership, client, scope)
    return {
        "id": client.public_id,
        "name": client.full_name,
        "initials": initials(client.full_name),
        "phone": mask_phone(client.phone) or None,
        "email": client.email if actions["edit"] else None,
        "notes": client.notes,
        "since": client.created_at,
        "activity": _activity(card, scope) if card["has_activity"] else None,
        "receivables": _receivables(membership, client, scope),
        "actions": actions,
    }


def duplicate_error(error: ValidationError) -> ValidationError:
    """El aviso de duplicado con el nombre del cliente que ya existe, nunca sus demás datos; el código no cambia."""
    code = getattr(error, "code", None)
    params = getattr(error, "params", None) or {}
    if code == "duplicate_client" and "existing_client" in params:
        names = Client.objects.filter(public_id=params["existing_client"]).values_list("full_name", flat=True)
        return ValidationError(f"{DUPLICATE_CLIENT[:-1]}: {', '.join(names)}.", code=code)
    if code == "possible_duplicate":
        names = Client.objects.filter(public_id__in=params["possible_duplicates"]).values_list("full_name", flat=True)
        return ValidationError(f"{POSSIBLE_DUPLICATE} Con ese nombre: {', '.join(names)}.", code=code)
    return error
