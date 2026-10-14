from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    # Sin versión, modo ni nombre de sistema: no se entrega información al atacante.
    return JsonResponse({"status": "ok"})
