"""La sesión de Django como única autenticación de la API, con el token CSRF vencido distinguible."""

from drf_spectacular.authentication import SessionScheme
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request


class CsrfFailed(PermissionDenied):
    """El token CSRF no corresponde a la sesión (por ejemplo, se inició sesión de nuevo en otra pestaña)."""

    default_code = "csrf_failed"


class SessionWithCsrfAuthentication(SessionAuthentication):
    """La misma `SessionAuthentication`; solo cambia el código del rechazo por CSRF.

    Sin esto, un token vencido respondería como una falta de permiso y la app diría "No tienes acceso" en vez
    de recargar la sesión.
    """

    def enforce_csrf(self, request: Request) -> None:
        try:
            super().enforce_csrf(request)
        except PermissionDenied as exc:
            raise CsrfFailed from exc


class SessionWithCsrfScheme(SessionScheme):
    """En el esquema OpenAPI es la misma cookie de sesión de siempre."""

    target_class = SessionWithCsrfAuthentication
