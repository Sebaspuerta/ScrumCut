from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.accounts.models import Theme
from apps.core.vite_manifest import read_entry

REACT_APP_ENTRY = "src/main.tsx"  # la entrada de vite.config.ts


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    # Sin versión, modo ni nombre de sistema: no se entrega información al atacante.
    return JsonResponse({"status": "ok"})


@require_GET
@login_required
def react_app(request: HttpRequest, subpath: str = "") -> HttpResponse:
    """La página de la app de React en /app/ y sus subrutas: el enrutador del navegador elige la pantalla.

    Solo entrega el HTML con los archivos compilados; los datos y los permisos llegan por la API.
    """
    entry = read_entry(settings.REACT_APP_MANIFEST, REACT_APP_ENTRY)
    # Con un tema elegido, el HTML ya lo trae y la página no parpadea; con "system" manda prefers-color-scheme.
    theme = request.user.theme if request.user.theme != Theme.SYSTEM else None
    return render(request, "app/index.html", {"entry": entry, "theme": theme})
