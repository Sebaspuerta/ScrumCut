"""En producción no se abre el registro sin los documentos legales publicados (Ley 1581 de 2012)."""

from django.core.checks import Error, register
from django.db import DatabaseError

from apps.legal.selectors import missing_signup_documents, sample_documents_in_force


@register("legal", deploy=True)
def no_sample_documents_in_force(app_configs, **kwargs) -> list[Error]:
    """El texto de ejemplo que publica cargar_demo nunca puede regir en producción."""
    try:
        samples = sample_documents_in_force()
    except DatabaseError:
        return []  # signup_documents_published ya informa que no se pudo leer la base
    if not samples:
        return []
    return [
        Error(
            f"Rige un texto de ejemplo, no válido para producción: {', '.join(samples)}.",
            hint="Publica la versión aprobada por Sebastián en apps.legal; la de ejemplo es solo para desarrollo.",
            id="legal.E003",
        )
    ]


@register("legal", deploy=True)
def signup_documents_published(app_configs, **kwargs) -> list[Error]:
    try:
        missing = missing_signup_documents()
    except DatabaseError:
        return [
            Error(
                "No se pudo verificar que los documentos legales estén publicados.",
                hint="El chequeo necesita la base de datos con las migraciones aplicadas.",
                id="legal.E002",
            )
        ]
    if not missing:
        return []
    return [
        Error(
            f"Falta una versión publicada de: {', '.join(missing)}.",
            hint="Publica los documentos aprobados en apps.legal; sin ellos el registro está cerrado.",
            id="legal.E001",
        )
    ]
