"""Errores de la API: un mensaje genérico al cliente y el detalle solo en los logs (regla 12)."""

import logging

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


def generic_error_handler(exc: Exception, context: dict) -> Response | None:
    """Las excepciones que DRF conoce salen con su código y un texto fijo; las demás siguen a Django (500)."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    view = context.get("view")
    logger.info("API %s respondió %s: %s", type(view).__name__, response.status_code, response.data)
    response.data = {"detail": GENERIC_MESSAGES.get(response.status_code, DEFAULT_MESSAGE)}
    return response
