import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.text import slugify
from django.views.decorators.http import require_GET

from apps.reports.excel.builder import build_business_report
from apps.reports.forms import PeriodFilterForm
from apps.reports.selectors.dashboard import executive_dashboard
from apps.sales.selectors import local_today, my_cuts_today, period_dates
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import require_permission
from apps.tenancy.roles import role_has_permission

logger = logging.getLogger(__name__)

TEMPLATE = "dashboard/home.html"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _filters(request: HttpRequest, membership: Membership) -> PeriodFilterForm:
    branches = Branch.objects.filter(is_active=True).order_by("name")
    return PeriodFilterForm(request.GET, branches=branches, today=local_today(membership))


@require_GET
@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Tablero completo con reportes.ver; el barbero ve solo sus cortes de hoy, sin cifras de dinero."""
    membership = request.membership
    if membership is None:
        return render(request, TEMPLATE, {"state": "empty"})
    if not role_has_permission(membership.role, "reportes.ver"):
        return render(request, TEMPLATE, {"state": "cuts", "cuts": my_cuts_today(membership)})
    form = _filters(request, membership)
    try:
        data = executive_dashboard(membership, *form.dates(), form.branch())
    except Exception:  # noqa: BLE001 — cualquier falla muestra el error genérico (regla 12); el detalle va al log
        logger.exception("No se pudo armar el tablero de la barbería %s", membership.barbershop_id)
        return render(request, TEMPLATE, {"state": "error", "form": form})
    return render(request, TEMPLATE, {"state": "ready", "form": form, "dashboard": data})


@require_GET
@require_permission("reportes.exportar")
def export(request: HttpRequest) -> HttpResponse:
    """El Excel de la sede y el período que se ven en el tablero. El nombre lleva barbería, sede y fechas."""
    membership = request.membership
    form = _filters(request, membership)
    branch = form.branch()
    date_from, date_to = period_dates(membership, *form.dates())
    response = HttpResponse(build_business_report(membership, date_from, date_to, branch), content_type=XLSX)
    sede = f"-{slugify(branch.name)}" if branch else ""
    name = f"scrumcut-{membership.barbershop.slug}{sede}-{date_from:%Y%m%d}-{date_to:%Y%m%d}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response
