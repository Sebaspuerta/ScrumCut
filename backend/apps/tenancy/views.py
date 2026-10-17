from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.tenancy.forms import BranchSwitchForm
from apps.tenancy.middleware import BRANCH_SESSION_KEY
from apps.tenancy.services import choose_branch


def _safe_next(request: HttpRequest, target: str) -> str:
    """La página anterior solo si es de este sitio; si no (redirección abierta), el tablero."""
    allowed = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if target and allowed else reverse("home")


@require_POST
@login_required
def switch_branch(request: HttpRequest) -> HttpResponse:
    """Cambia la sede activa entre las permitidas al rol; una sede no permitida responde 403."""
    form = BranchSwitchForm(request.POST)
    if request.membership is None or not form.is_valid():
        raise PermissionDenied
    scope = choose_branch(request.membership, form.cleaned_data["sede"])
    request.session[BRANCH_SESSION_KEY] = scope.token
    return redirect(_safe_next(request, form.cleaned_data["next"]))
