"""Páginas de error de Django: 400, 403, 404, 500 y el fallo de CSRF.

Se pintan sin la petición: sin context processors, sin sesión y sin base de datos. Así la 500 se muestra
aunque todo lo demás falle, y ninguna enseña detalles técnicos (hallazgo S6 de docs/arquitectura.md).
"""

from http import HTTPStatus

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template import loader


def _page(template: str, status: HTTPStatus) -> HttpResponse:
    # El contacto de soporte sale de settings, no de la base de datos.
    html = loader.get_template(f"errors/{template}.html").render({"support_email": settings.SUPPORT_EMAIL})
    return HttpResponse(html, status=status)


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    return _page("400", HTTPStatus.BAD_REQUEST)


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    return _page("403", HTTPStatus.FORBIDDEN)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return _page("404", HTTPStatus.NOT_FOUND)


def server_error(request: HttpRequest) -> HttpResponse:
    return _page("500", HTTPStatus.INTERNAL_SERVER_ERROR)


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    """El motivo de Django (`reason`) es técnico: se queda en los logs, nunca en la página."""
    return _page("csrf", HTTPStatus.FORBIDDEN)
