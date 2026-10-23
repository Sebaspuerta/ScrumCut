"""Rutas de la pantalla de Clientes (fase F4)."""

from django.urls import path

from apps.clients import views

urlpatterns = [
    path("", views.board, name="clients_board"),
    path("nuevo/", views.create, name="clients_new"),
    path("<uuid:public_id>/", views.detail, name="clients_detail"),
    path("<uuid:public_id>/editar/", views.edit, name="clients_edit"),
]
