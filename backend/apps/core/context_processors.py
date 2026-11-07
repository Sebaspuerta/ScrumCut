"""Lo que necesitan las plantillas de la entrada además de su vista."""

from django.conf import settings
from django.http import HttpRequest


def support(request: HttpRequest) -> dict:
    """El contacto de ScrumTech para los textos de la entrada; vacío en desarrollo, y entonces se omite."""
    return {"support_email": settings.SUPPORT_EMAIL}
