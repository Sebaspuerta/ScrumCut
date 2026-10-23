from django.urls import path

from apps.api import views

urlpatterns = [
    path("me/", views.MeView.as_view(), name="api_me"),
    path("navigation/", views.NavigationView.as_view(), name="api_navigation"),
    path("branch/", views.BranchView.as_view(), name="api_branch"),
    path("csrf/", views.CsrfView.as_view(), name="api_csrf"),
    path("me/preferences/", views.PreferencesView.as_view(), name="api_preferences"),
    path("notifications/", views.NotificationsView.as_view(), name="api_notifications"),
    path("dashboard/", views.DashboardView.as_view(), name="api_dashboard"),
]
