from django.urls import path

from apps.api import cash_views, order_views, views

urlpatterns = [
    path("me/", views.MeView.as_view(), name="api_me"),
    path("navigation/", views.NavigationView.as_view(), name="api_navigation"),
    path("branch/", views.BranchView.as_view(), name="api_branch"),
    path("csrf/", views.CsrfView.as_view(), name="api_csrf"),
    path("me/preferences/", views.PreferencesView.as_view(), name="api_preferences"),
    path("notifications/", views.NotificationsView.as_view(), name="api_notifications"),
    path("dashboard/", views.DashboardView.as_view(), name="api_dashboard"),
    path("orders/", order_views.OrderListView.as_view(), name="api_orders"),
    path("orders/create/", order_views.OrderCreateView.as_view(), name="api_order_create"),
    path("orders/catalog/", order_views.OrderCatalogView.as_view(), name="api_order_catalog"),
    path("orders/<uuid:public_id>/", order_views.OrderDetailView.as_view(), name="api_order"),
    path("orders/<uuid:public_id>/client/", order_views.OrderClientView.as_view(), name="api_order_client"),
    path("orders/<uuid:public_id>/lines/", order_views.OrderLinesView.as_view(), name="api_order_lines"),
    path(
        "orders/<uuid:public_id>/lines/<uuid:item>/remove/",
        order_views.OrderLineRemoveView.as_view(),
        name="api_order_line_remove",
    ),
    path("orders/<uuid:public_id>/discount/", order_views.OrderDiscountView.as_view(), name="api_order_discount"),
    path("orders/<uuid:public_id>/checkout/", order_views.OrderCheckoutView.as_view(), name="api_order_checkout"),
    path("orders/<uuid:public_id>/cancel/", order_views.OrderCancelView.as_view(), name="api_order_cancel"),
    path("clients/search/", order_views.ClientSearchView.as_view(), name="api_client_search"),
    path("cash/", cash_views.CashView.as_view(), name="api_cash"),
    path("cash/open/", cash_views.CashOpenView.as_view(), name="api_cash_open"),
    path("cash/closings/", cash_views.CashClosingsView.as_view(), name="api_cash_closings"),
    path("cash/<uuid:session>/movements/", cash_views.CashMovementView.as_view(), name="api_cash_movement"),
    path("cash/<uuid:session>/close/", cash_views.CashCloseView.as_view(), name="api_cash_close"),
]
