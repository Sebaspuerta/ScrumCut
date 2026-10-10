from django.http import HttpRequest

from apps.core.http import client_ip
from apps.legal.models import Acceptance
from apps.legal.selectors import ACCEPTED_AT_SIGNUP, current_document


def accept_signup_documents(user, request: HttpRequest) -> list[Acceptance]:
    """Evidencia de la autorización previa del titular: qué versión aceptó, cuándo y desde qué IP."""
    ip = client_ip(request)
    return [
        Acceptance.objects.create(document=current_document(kind), user=user, ip_address=ip)
        for kind in ACCEPTED_AT_SIGNUP
    ]
