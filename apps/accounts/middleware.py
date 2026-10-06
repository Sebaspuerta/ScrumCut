"""2FA obligatorio para dueños, administradores y superadmin de plataforma."""

from collections.abc import Callable

from allauth.mfa.models import Authenticator
from allauth.mfa.utils import is_mfa_enabled
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.tenancy.roles import PRIVILEGED_ROLES

# Rutas que deben seguir accesibles mientras el usuario configura su 2FA.
_ALLOWED_PREFIXES = ("/cuenta/", "/static/", "/salud/")


class RequireMFAForPrivilegedRolesMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._must_enroll(request):
            return redirect(reverse("mfa_activate_totp"))
        return self.get_response(request)

    @staticmethod
    def _must_enroll(request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if request.path.startswith(_ALLOWED_PREFIXES):
            return False
        membership = getattr(request, "membership", None)
        privileged = user.is_platform_staff or (membership is not None and membership.role in PRIVILEGED_ROLES)
        return privileged and not is_mfa_enabled(user, [Authenticator.Type.TOTP])
