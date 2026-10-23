"""Pantalla de Clientes (fase F4): cifras de la sede, lista con filtros, ficha y formularios.

Las vistas solo reciben, validan el formato y responden; leen con `apps.clients.board` y
`apps.clients.profile`, y escriben con `apps.clients.services` (duplicados, autorización de datos y
auditoría). La persona es de la barbería; su historial, nivel y deuda, de las sedes del alcance.
"""

from uuid import UUID

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.clients import services
from apps.clients.board import ClientFilter, client_rows, client_stats
from apps.clients.forms import LEVELS, ClientFilterForm, ClientForm, NewClientForm
from apps.clients.models import Client
from apps.clients.profile import client_card
from apps.legal.models import LegalDocument
from apps.legal.selectors import current_document
from apps.sales.selectors import day_bounds, local_today
from apps.tenancy.permissions import require_permission
from apps.tenancy.roles import role_has_permission

BOARD = "clients/board.html"
ORDER_LABELS = (
    ("ultima", "Última visita"),
    ("visitas", "Más visitas"),
    ("gasto", "Mayor gasto"),
    ("deuda", "Mayor deuda"),
)
FORM = "clients/form.html"
PERMISSIONS = {"create": "clientes.crear", "edit": "clientes.editar", "new_order": "comandas.crear"}


def _month_start(membership):
    today = local_today(membership)
    return day_bounds(membership.barbershop.timezone, today.replace(day=1), today)[0]


def _chips(counts: dict, filters: ClientFilter) -> list[dict]:
    total = sum(counts.values())
    return [
        {
            "value": value,
            "label": label,
            "count": counts.get(value, 0) if value else total,
            "on": value == filters.level,
        }
        for value, label in LEVELS
    ]


def _board(request: HttpRequest) -> dict:
    membership, scope, now = request.membership, request.branch_scope, timezone.now()
    filters = ClientFilterForm(request.GET).filters()
    page, counts = client_rows(membership, scope=scope, filters=filters, now=now, page=request.GET.get("pagina", 1))
    return {
        "filters": filters,
        "orderings": ORDER_LABELS,
        "page": page,
        "chips": _chips(counts, filters),
        "stats": client_stats(membership, scope=scope, now=now, month_start=_month_start(membership)),
        "can": {name: role_has_permission(membership.role, code) for name, code in PERMISSIONS.items()},
    }


@require_GET
@require_permission("clientes.ver")
def board(request: HttpRequest) -> HttpResponse:
    return render(request, BOARD, _board(request))


@require_GET
@require_permission("clientes.ver")
def detail(request: HttpRequest, public_id: UUID) -> HttpResponse:
    try:
        card = client_card(request.membership, public_id, scope=request.branch_scope)
    except Client.DoesNotExist as exc:
        raise Http404 from exc
    return render(request, BOARD, {**_board(request), "card": card})


def _duplicate_notice(error: ValidationError) -> dict:
    """Solo el nombre del cliente que ya existe (y su ficha), nunca sus demás datos."""
    params = getattr(error, "params", None) or {}
    if error.code == "duplicate_client" and "existing_client" in params:
        existing = Client.objects.filter(public_id=params["existing_client"]).first()
        return {"duplicate": existing}
    if error.code == "possible_duplicate":
        return {"similar": list(Client.objects.filter(public_id__in=params["possible_duplicates"]))}
    return {"error": " ".join(error.messages)}


def _render_form(request: HttpRequest, form, *, client=None, **extra) -> HttpResponse:
    return render(request, FORM, {"form": form, "client": client, **extra})


@require_http_methods(["GET", "POST"])
@require_permission("clientes.crear")
def create(request: HttpRequest) -> HttpResponse:
    """Con la autorización de datos y la versión vigente de la política; sin política publicada no se crea."""
    policy = current_document(LegalDocument.Kind.DATA_POLICY)
    form = NewClientForm(request.POST or None)
    if policy is None or request.method == "GET" or not form.is_valid():
        return _render_form(request, form, missing_policy=policy is None)
    try:
        client = services.create_client(
            request.membership,
            form.client_data(),
            data_consent_at=timezone.now(),
            data_policy_version=policy.version,
            force=form.cleaned_data["other_person"],
        )
    except ValidationError as error:
        return _render_form(request, form, **_duplicate_notice(error))
    messages.success(request, f"Cliente {client.full_name} creado.")
    return redirect(reverse("clients_detail", args=[client.public_id]))


@require_http_methods(["GET", "POST"])
@require_permission("clientes.editar")
def edit(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """Los cambios quedan en la auditoría (`update_client`); el documento nunca se guarda en claro."""
    client = Client.objects.filter(public_id=public_id, deleted_at__isnull=True).first()
    if client is None:
        raise Http404
    initial = {"full_name": client.full_name, "email": client.email, "notes": client.notes}
    form = ClientForm(request.POST or None, initial=initial)
    if request.method == "GET" or not form.is_valid():
        return _render_form(request, form, client=client)
    try:
        services.update_client(request.membership, public_id, data=_changed(form))
    except ValidationError as error:
        return _render_form(request, form, client=client, **_duplicate_notice(error))
    messages.success(request, "Datos del cliente actualizados.")
    return redirect(reverse("clients_detail", args=[public_id]))


def _changed(form: ClientForm) -> dict:
    """Celular y cédula no se muestran al editar: solo se cambian si se escribe un valor nuevo."""
    data = form.client_data()
    return {field: value for field, value in data.items() if field not in ("phone", "document") or value}
