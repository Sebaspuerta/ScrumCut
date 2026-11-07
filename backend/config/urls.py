from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as account_views
from apps.core import views as core_views
from apps.reports import views as report_views

urlpatterns = [
    path(f"{settings.ADMIN_URL.strip('/')}/", admin.site.urls),
    path("cuenta/cerrar-sesiones/", account_views.logout_everywhere, name="logout_everywhere"),
    # Antes que allauth: su /cuenta/inactive/ queda retirada (hallazgo S4).
    path("cuenta/inactive/", account_views.inactive_page_retired, name="account_inactive_retired"),
    path("cuenta/", include("allauth.urls")),
    path("legal/", include("apps.legal.urls")),
    path("salud/", core_views.health, name="health"),
    path("api/v1/", include("apps.api.urls")),
    path("app/", core_views.react_app, name="react_app"),
    path("app/<path:subpath>", core_views.react_app, name="react_app_route"),
    path("reportes/exportar/", report_views.export, name="reports_export"),
    path("", include("apps.core.legacy_urls")),
]

handler400 = "apps.core.errors.bad_request"
handler403 = "apps.core.errors.permission_denied"
handler404 = "apps.core.errors.page_not_found"
handler500 = "apps.core.errors.server_error"
