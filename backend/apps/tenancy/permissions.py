"""Autorización en el servidor. Ocultar botones en la interfaz es solo estética."""

from collections.abc import Callable
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from apps.core.tenant_context import get_current_barbershop_id
from apps.tenancy.roles import role_has_permission


def ensure_member(membership) -> None:
    """La membresía está activa y es de la barbería activa. Si no, `PermissionDenied`."""
    if membership is None or not membership.is_active or membership.barbershop_id != get_current_barbershop_id():
        raise PermissionDenied


def ensure_permission(membership, code: str) -> None:
    """Para services y selectors: además de `ensure_member`, el rol debe tener el permiso."""
    ensure_member(membership)
    if not role_has_permission(membership.role, code):
        raise PermissionDenied


def require_permission(code: str) -> Callable:
    """Exige sesión iniciada (si no, al login) y el permiso en la barbería activa (si no, 403)."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs):
            membership = getattr(request, "membership", None)
            if membership is None or not role_has_permission(membership.role, code):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        # La prueba que recorre las URLs lee esta marca: una vista sin ella falla.
        wrapper.required_permission = code
        return login_required(wrapper)

    return decorator
