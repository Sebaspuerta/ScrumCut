from zoneinfo import ZoneInfo

from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_GET

from apps.reports.excel.builder import build_business_report
from apps.reports.forms import MonthFilterForm
from apps.reports.selectors.calendar import month_bounds
from apps.sales.selectors import local_today
from apps.tenancy.models import Membership
from apps.tenancy.permissions import require_permission

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _filters(request: HttpRequest, membership: Membership) -> MonthFilterForm:
    since = timezone.localdate(membership.barbershop.created_at, ZoneInfo(membership.barbershop.timezone))
    return MonthFilterForm(request.GET, today=local_today(membership), since=since)


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
