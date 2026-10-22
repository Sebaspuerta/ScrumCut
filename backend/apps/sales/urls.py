"""Rutas de la pantalla de Comandas (fase F3)."""

from django.urls import path

from apps.sales import actions, views

urlpatterns = [
    path("", views.board, name="orders_board"),
    path("nueva/", views.new_order, name="orders_new"),
    path("nueva/crear/", actions.create, name="orders_create"),
    path("cobro-rapido/", views.quick_charge, name="orders_quick"),
    path("cobro-rapido/cobrar/", actions.quick, name="orders_quick_charge"),
    path("<uuid:public_id>/", views.detail, name="orders_detail"),
    path("<uuid:public_id>/cliente/", actions.change_client, name="orders_change_client"),
    path("<uuid:public_id>/lineas/", actions.add_line, name="orders_add_line"),
    path("<uuid:public_id>/lineas/<uuid:item>/quitar/", actions.remove_line, name="orders_remove_line"),
    path("<uuid:public_id>/descuento/", actions.discount, name="orders_discount"),
    path("<uuid:public_id>/cobrar/", actions.checkout, name="orders_checkout"),
    path("<uuid:public_id>/anular/", actions.cancel, name="orders_cancel"),
]
