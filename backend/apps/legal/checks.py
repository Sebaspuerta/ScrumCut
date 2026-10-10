"""En producción no se abre el registro sin los documentos legales publicados (Ley 1581 de 2012)."""

from django.core.checks import Error, register
from django.db import DatabaseError

from apps.legal.selectors import missing_signup_documents


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
