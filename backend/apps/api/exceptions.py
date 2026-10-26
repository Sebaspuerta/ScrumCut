"""Errores de la API: una sola forma para toda /api/v1/ y el detalle técnico solo en los logs (regla 12).

Todo error responde `{"detail", "code", "field_errors"}`. `detail` es un texto fijo por código HTTP o, en
una validación, el mensaje para el usuario: los mismos textos en español de las pantallas de Django, nunca
`str(e)`. `field_errors` trae los mensajes de cada campo (vacío si no aplica) y `code`, qué pasó.
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

GENERIC_MESSAGES = {
    400: "Revisa los datos enviados.",
    401: "Inicia sesión para continuar.",
    403: "No tienes permiso para esta acción.",
    404: "No encontramos lo que buscas.",
    405: "Esta acción no está disponible.",
    429: "Demasiadas solicitudes. Intenta de nuevo en un momento.",
}
DEFAULT_MESSAGE = "No pudimos completar la solicitud."
# Qué pasó, para que el cliente decida sin leer el texto. Un ValidationError de un service trae el suyo.
STATUS_CODES = {
    400: "invalid",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    429: "throttled",
}
DEFAULT_CODE = "error"
NON_FIELD_KEYS = {"__all__", "non_field_errors"}


class ServiceValidationError(ValidationError):
    """Un `ValidationError` de Django (service o formulario), con su código si lo trae (`stale_session`)."""

    def __init__(self, error: DjangoValidationError) -> None:
        by_field = hasattr(error, "error_dict")
        super().__init__(error.message_dict if by_field else {"__all__": error.messages})
        self.service_code = None if by_field else next((item.code for item in error.error_list if item.code), None)


def _as_drf(exc: Exception) -> Exception:
    """Un objeto inexistente o fuera del alcance responde 404, sin revelar si existe; un ValidationError, 400."""
    if isinstance(exc, ObjectDoesNotExist):
        return Http404()
    if isinstance(exc, DjangoValidationError):
        return ServiceValidationError(exc)
    return exc


def _messages(value) -> list[str]:
    if isinstance(value, dict):
        return [message for nested in value.values() for message in _messages(nested)]
    if isinstance(value, list):
        return [message for item in value for message in _messages(item)]
    return [str(value)]


def _field_name(key: str, exc: ValidationError, error_fields: dict[str, str]) -> str | None:
    """Los campos del serializer ya traen su nombre en la API. Los de los services y formularios traen el suyo
    (`recibido`, `notes`...): la vista lo traduce con `error_fields`, y lo que no está ahí va en `detail`."""
    if key in NON_FIELD_KEYS:
        return None
    return error_fields.get(key) if isinstance(exc, ServiceValidationError) else key


def _validation_body(exc: ValidationError, error_fields: dict[str, str]) -> dict:
    data = exc.detail if isinstance(exc.detail, dict) else {"__all__": exc.detail}
    fields: dict[str, list[str]] = {}
    general: list[str] = []
    for key, value in data.items():
        name = _field_name(key, exc, error_fields)
        if name is None:
            general += _messages(value)
        else:
            fields.setdefault(name, []).extend(_messages(value))
    return {
        "detail": " ".join(general) or GENERIC_MESSAGES[400],
        "code": getattr(exc, "service_code", None) or STATUS_CODES[400],
        "field_errors": fields,
    }


def _status_body(status_code: int) -> dict:
    return {
        "detail": GENERIC_MESSAGES.get(status_code, DEFAULT_MESSAGE),
        "code": STATUS_CODES.get(status_code, DEFAULT_CODE),
        "field_errors": {},
    }


def generic_error_handler(exc: Exception, context: dict) -> Response | None:
    """Las excepciones que DRF conoce salen con su código y la forma común; las demás siguen a Django (500)."""
    view = context.get("view")
    exc = _as_drf(exc)
    response = exception_handler(exc, context)
    if response is None:
        return None
    logger.info("API %s respondió %s: %s", type(view).__name__, response.status_code, response.data)
    if isinstance(exc, ValidationError):
        response.data = _validation_body(exc, getattr(view, "error_fields", {}))
    else:
        response.data = _status_body(response.status_code)
    return response
