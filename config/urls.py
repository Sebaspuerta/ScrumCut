from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path(f"{settings.ADMIN_URL.strip('/')}/", admin.site.urls),
    path("cuenta/", include("allauth.urls")),
    path("salud/", core_views.health, name="health"),
    path("", core_views.home, name="home"),
]
