"""Lectura pública de los documentos legales vigentes, en texto plano y sin diseño."""

from django.http import Http404, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET

from apps.legal.models import LegalDocument
from apps.legal.selectors import current_document

DOCUMENT_SLUGS = {
    "terminos": LegalDocument.Kind.TERMS,
    "tratamiento-de-datos": LegalDocument.Kind.DATA_POLICY,
    "privacidad": LegalDocument.Kind.PRIVACY_NOTICE,
    "cookies": LegalDocument.Kind.COOKIES,
}


@require_GET
def document(request: HttpRequest, slug: str) -> HttpResponse:
    kind = DOCUMENT_SLUGS.get(slug)
    current = current_document(kind) if kind else None
    if current is None:
        raise Http404
    return HttpResponse(current.body, content_type="text/plain; charset=utf-8")
