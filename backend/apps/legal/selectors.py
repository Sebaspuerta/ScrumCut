"""Lecturas de documentos legales. Los textos los aprueba una persona; aquí solo se elige la versión vigente."""

from django.utils import timezone

from apps.legal.models import LegalDocument

Kind = LegalDocument.Kind

# Sin una versión publicada de cada uno, el registro queda cerrado (Ley 1581 de 2012).
REQUIRED_FOR_SIGNUP = (Kind.TERMS, Kind.DATA_POLICY, Kind.PRIVACY_NOTICE)
ACCEPTED_AT_SIGNUP = (Kind.TERMS, Kind.DATA_POLICY)

# Marca de los textos de ejemplo (cargar_demo): sirven para desarrollar, nunca para producción.
SAMPLE_VERSION_PREFIX = "ejemplo-"
SAMPLE_BODY = "Texto de ejemplo, no válido para producción."


def current_document(kind: str) -> LegalDocument | None:
    """La versión publicada más reciente; una con fecha futura todavía no rige."""
    return (
        LegalDocument.objects.filter(kind=kind, published_at__isnull=False, published_at__lte=timezone.now())
        .order_by("-published_at", "-pk")
        .first()
    )


def missing_signup_documents() -> list[str]:
    return [kind for kind in REQUIRED_FOR_SIGNUP if current_document(kind) is None]


def sample_documents_in_force() -> list[str]:
    """Los documentos cuya versión vigente es de ejemplo (versión con `SAMPLE_VERSION_PREFIX`)."""
    current = (current_document(kind) for kind in REQUIRED_FOR_SIGNUP)
    return [document.kind for document in current if document and document.version.startswith(SAMPLE_VERSION_PREFIX)]
