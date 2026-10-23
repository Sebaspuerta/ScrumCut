"""Rutas de la pantalla de Fiados (fase F4)."""

from django.urls import path

from apps.receivables import views

urlpatterns = [
    path("", views.board, name="receivables_board"),
    path("<uuid:public_id>/", views.detail, name="receivables_detail"),
    path("<uuid:public_id>/abonar/", views.pay, name="receivables_pay"),
]
