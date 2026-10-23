"""Autorización de la API: la misma matriz de `roles.py` que usan las vistas con plantillas."""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.tenancy.roles import role_has_permission


class HasRolePermission(BasePermission):
    """Membresía activa en la barbería activa y, si la vista lo declara, su permiso (`required_permission`).

    La membresía la fija `ActiveBarbershopMiddleware`; sin ella (ninguna barbería o varias) no hay acceso.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        membership = getattr(request, "membership", None)
        if membership is None:
            return False
        code = getattr(view, "required_permission", None)
        return code is None or role_has_permission(membership.role, code)
