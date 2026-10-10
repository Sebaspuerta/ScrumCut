from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as account_views
from apps.core import views as core_views

urlpatterns = [
    path(f"{settings.ADMIN_URL.strip('/')}/", admin.site.urls),
    path("cuenta/cerrar-sesiones/", account_views.logout_everywhere, name="logout_everywhere"),
    path("cuenta/", include("allauth.urls")),
    path("legal/", include("apps.legal.urls")),
    path("salud/", core_views.health, name="health"),
    path("", core_views.home, name="home"),
]
