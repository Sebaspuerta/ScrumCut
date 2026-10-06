"""Autorización en el servidor. Ocultar botones en la interfaz es solo estética."""

from collections.abc import Callable
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from apps.tenancy.roles import role_has_permission


def require_permission(code: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs):
            membership = getattr(request, "membership", None)
            if membership is None or not role_has_permission(membership.role, code):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
