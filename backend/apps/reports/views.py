import logging
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_GET

from apps.reports.excel.builder import build_business_report
from apps.reports.forms import MonthFilterForm
from apps.reports.selectors.calendar import month_bounds
from apps.reports.selectors.dashboard import executive_dashboard
from apps.sales.selectors import local_today, my_cuts_today
from apps.tenancy.models import Membership
from apps.tenancy.permissions import require_permission
from apps.tenancy.roles import role_has_permission

logger = logging.getLogger(__name__)

TEMPLATE = "dashboard/home.html"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _filters(request: HttpRequest, membership: Membership) -> MonthFilterForm:
    since = timezone.localdate(membership.barbershop.created_at, ZoneInfo(membership.barbershop.timezone))
    return MonthFilterForm(request.GET, today=local_today(membership), since=since)


def _ready(request: HttpRequest, membership: Membership, form: MonthFilterForm) -> dict:
    data = executive_dashboard(membership, form.month(), scope=request.branch_scope)
    can_export = role_has_permission(membership.role, "reportes.exportar")
    return {"state": "ready", "form": form, "dashboard": data, "can_export": can_export, "view": form.view()}


@require_GET
@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Tablero completo con reportes.ver; el barbero ve solo sus cortes de hoy, sin cifras de dinero."""
    membership = request.membership
    if membership is None:
        return render(request, TEMPLATE, {"state": "empty"})
    if not role_has_permission(membership.role, "reportes.ver"):
        cuts = my_cuts_today(membership, scope=request.branch_scope)
        return render(request, TEMPLATE, {"state": "cuts", "cuts": cuts})
    form = _filters(request, membership)
    try:
        context = _ready(request, membership, form)
    except Exception:  # noqa: BLE001 — cualquier falla muestra el error genérico (regla 12); el detalle va al log
        logger.exception("No se pudo armar el tablero de la barbería %s", membership.barbershop_id)
        return render(request, TEMPLATE, {"state": "error", "form": form})
    return render(request, TEMPLATE, context)


@require_GET
@require_permission("reportes.exportar")
def export(request: HttpRequest) -> HttpResponse:
    """El Excel del alcance y del mes que se ven en el tablero (el mes en curso, hasta hoy). El nombre
    lleva barbería, sede y fechas; en "todas", sin sede."""
    membership = request.membership
    scope = request.branch_scope
    form = _filters(request, membership)
    date_from, last = month_bounds(form.month())
    date_to = min(last, local_today(membership))
    report = build_business_report(membership, date_from, date_to, scope=scope)
    response = HttpResponse(report, content_type=XLSX)
    sede = f"-{slugify(scope.branch.name)}" if scope.branch else ""
    name = f"scrumcut-{membership.barbershop.slug}{sede}-{date_from:%Y%m%d}-{date_to:%Y%m%d}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response
