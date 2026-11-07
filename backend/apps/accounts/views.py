from http import HTTPStatus
from typing import NoReturn

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.adapter import LOCKOUT_MESSAGE
from apps.accounts.services import logout_all_devices


@require_POST
@login_required
def logout_everywhere(request: HttpRequest) -> HttpResponse:
    logout_all_devices(request.user, request)
    logout(request)
    return redirect("account_login")


def inactive_page_retired(request: HttpRequest) -> NoReturn:
    """La pantalla de allauth para cuentas inactivas revelaba que la cuenta existe (hallazgo S4): ya no existe."""
    raise Http404


def lockout(request: HttpRequest, original_response: HttpResponse | None, credentials: dict | None) -> HttpResponse:
    """La respuesta de axes al pausar el ingreso: el mismo mensaje exista o no la cuenta (hallazgo S4)."""
    return render(request, "account/lockout.html", {"message": LOCKOUT_MESSAGE}, status=HTTPStatus.TOO_MANY_REQUESTS)
