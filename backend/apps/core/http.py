from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str | None:
    # Detrás de Cloudflare la IP real llega en CF-Connecting-IP (Nginx solo acepta rangos de Cloudflare).
    return request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR")
