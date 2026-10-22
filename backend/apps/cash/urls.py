"""Rutas de la pantalla de Caja (fase F3)."""

from django.urls import path

from apps.cash import views

urlpatterns = [
    path("", views.register, name="cash_register"),
    path("abrir/", views.open_session, name="cash_open"),
    # Antes que la de movimientos: "cerrar" también encajaría como tipo de movimiento.
    path("<uuid:session>/cerrar/", views.close_session, name="cash_close"),
    path("<uuid:session>/<slug:kind>/", views.manual_movement, name="cash_movement"),
]
