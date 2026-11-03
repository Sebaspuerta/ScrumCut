"""Fase R5: las direcciones de las pantallas de plantillas llevan, de forma permanente, a su pantalla en React."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.tenancy.roles import Role
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

ID = "00000000-0000-0000-0000-000000000001"
REDIRECTS = [
    ("/", "/app/"),
    ("/?mes=2026-10&vista=3d", "/app/?mes=2026-10&vista=3d"),
    ("/comandas/", "/app/comandas"),
    ("/comandas/?pestana=cerradas&q=ana", "/app/comandas?pestana=cerradas&q=ana"),
    ("/comandas/nueva/", "/app/comandas?nueva=1"),
    ("/comandas/cobro-rapido/", "/app/comandas?cobro=1"),
    (f"/comandas/{ID}/", f"/app/comandas?comanda={ID}"),
    ("/caja/", "/app/caja"),
    ("/caja/?tipo=gasto", "/app/caja?tipo=gasto"),
    ("/clientes/", "/app/clientes"),
    ("/clientes/?q=laura&nivel=vip", "/app/clientes?q=laura&nivel=vip"),
    ("/clientes/nuevo/", "/app/clientes?nuevo=1"),
    (f"/clientes/{ID}/", f"/app/clientes?cliente={ID}"),
    (f"/clientes/{ID}/editar/", f"/app/clientes?cliente={ID}&editar=1"),
    ("/fiados/", "/app/fiados"),
    (f"/fiados/{ID}/", f"/app/fiados?fiado={ID}"),
]


@pytest.mark.parametrize(("old", "new"), REDIRECTS)
def test_la_direccion_vieja_redirige_para_siempre_a_react(client, old, new):
    response = client.get(old)
    assert (response.status_code, response["Location"]) == (301, new)


def test_sin_sesion_la_redireccion_termina_en_el_login(client, built_app):
    response = client.get("/comandas/", follow=True)
    assert response.redirect_chain[-1][0].startswith(reverse("account_login"))


OLD_ACTIONS = [f"/comandas/{ID}/cobrar/", "/caja/abrir/", f"/fiados/{ID}/abonar/", "/sede/cambiar/"]


@pytest.mark.parametrize("action", OLD_ACTIONS)
def test_las_acciones_post_de_las_pantallas_viejas_ya_no_existen(world, action):
    client = Client()
    client.force_login(world.cashier.user)
    assert client.post(action).status_code == 404


def test_al_iniciar_sesion_se_llega_a_la_app_de_react(client, make_shop, make_member):
    make_member("barbero@example.com", make_shop("a"), Role.BARBER)
    response = client.post(reverse("account_login"), {"login": "barbero@example.com", "password": TEST_PASSWORD})
    assert (response.status_code, response["Location"]) == (302, reverse("react_app"))


def test_al_cerrar_sesion_se_llega_al_login_sin_pasar_por_las_direcciones_viejas(client, make_shop, make_member):
    client.force_login(make_member("barbero@example.com", make_shop("a"), Role.BARBER))
    response = client.post(reverse("account_logout"))
    assert (response.status_code, response["Location"]) == (302, reverse("account_login"))
