from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from apps.accounts.services import logout_all_devices


@require_POST
@login_required
def logout_everywhere(request: HttpRequest) -> HttpResponse:
    logout_all_devices(request.user, request)
    logout(request)
    return redirect("account_login")
