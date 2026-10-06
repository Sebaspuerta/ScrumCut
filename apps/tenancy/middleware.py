"""Fija la barbería activa de cada petición (barrera 1 y barrera 2)."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.tenant_context import tenant_context
from apps.tenancy import selectors

SESSION_KEY = "active_barbershop_id"


class ActiveBarbershopMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.barbershop = None
        request.membership = None

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            membership = self._resolve_membership(request)
            if membership is not None:
                request.membership = membership
                request.barbershop = membership.barbershop

        barbershop_id = request.barbershop.pk if request.barbershop else None
        with tenant_context(barbershop_id):
            return self.get_response(request)

    @staticmethod
    def _resolve_membership(request: HttpRequest):
        stored = request.session.get(SESSION_KEY)
        if stored is not None:
            membership = selectors.membership_for(request.user, stored)
            if membership is not None:
                return membership
            # La membresía ya no es válida (revocada, barbería suspendida): se olvida.
            request.session.pop(SESSION_KEY, None)

        memberships = selectors.active_memberships(request.user)
        if len(memberships) == 1:
            request.session[SESSION_KEY] = memberships[0].barbershop_id
            return memberships[0]
        # Cero o varias: la vista de selección de barbería decide (fase 1).
        return None
