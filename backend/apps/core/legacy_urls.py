"""Direcciones de las pantallas de plantillas que ya reemplazó la app de React (fase R5).

Redirigen de forma permanente a su pantalla en /app/, así siguen sirviendo los marcadores y los enlaces
viejos. No exigen sesión: solo redirigen, y /app/ la pide. Las acciones POST de esas pantallas no se
redirigen: ahora son de la API.
"""

from collections.abc import Callable

from django.http import HttpResponse
from django.urls import path
from django.views.generic import RedirectView

APP = "/app"  # la ruta de react_app en config/urls.py


def _to_app(target: str, *, keep_query: bool = False) -> Callable[..., HttpResponse]:
    """`keep_query` conserva los filtros de la dirección vieja (?mes=, ?q=, …): React usa los mismos."""
    return RedirectView.as_view(url=f"{APP}{target}", permanent=True, query_string=keep_query)


urlpatterns = [
    path("", _to_app("/", keep_query=True), name="legacy_home"),
    path("comandas/", _to_app("/comandas", keep_query=True), name="legacy_orders"),
    path("comandas/nueva/", _to_app("/comandas?nueva=1"), name="legacy_orders_new"),
    path("comandas/cobro-rapido/", _to_app("/comandas?cobro=1"), name="legacy_orders_quick"),
    path("comandas/<uuid:public_id>/", _to_app("/comandas?comanda=%(public_id)s"), name="legacy_order"),
    path("caja/", _to_app("/caja", keep_query=True), name="legacy_cash"),
    path("clientes/", _to_app("/clientes", keep_query=True), name="legacy_clients"),
    path("clientes/nuevo/", _to_app("/clientes?nuevo=1"), name="legacy_clients_new"),
    path("clientes/<uuid:public_id>/", _to_app("/clientes?cliente=%(public_id)s"), name="legacy_client"),
    path(
        "clientes/<uuid:public_id>/editar/",
        _to_app("/clientes?cliente=%(public_id)s&editar=1"),
        name="legacy_client_edit",
    ),
    path("fiados/", _to_app("/fiados", keep_query=True), name="legacy_receivables"),
    path("fiados/<uuid:public_id>/", _to_app("/fiados?fiado=%(public_id)s"), name="legacy_receivable"),
]
