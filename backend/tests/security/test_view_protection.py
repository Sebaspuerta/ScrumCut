"""Punto 2: los permisos se validan en el servidor. Una vista nueva sin protección hace fallar esta prueba."""

import pytest
from django.urls import reverse

from apps.tenancy.roles import ALL_PERMISSIONS
from tests.security.url_inventory import LOGIN_ONLY_VIEWS, PUBLIC_VIEWS, project_views, sample_path

pytestmark = pytest.mark.django_db

VIEWS = project_views()


@pytest.mark.parametrize(("route", "name", "view"), VIEWS, ids=[name or route for route, name, _ in VIEWS])
def test_cada_vista_exige_login_y_permiso_o_es_publica_con_motivo(client, route, name, view):
    if name in PUBLIC_VIEWS:
        return
    response = client.get(sample_path(route))
    if response.status_code == 405:  # vistas solo POST
        response = client.post(sample_path(route))

    assert response.status_code == 302 and response.url.startswith(reverse("account_login")), f"{route} sin login"
    assert name in LOGIN_ONLY_VIEWS or getattr(view, "required_permission", None) in ALL_PERMISSIONS, (
        f"{route} no declara un permiso de roles.py"
    )


def test_las_listas_de_excepciones_no_tienen_vistas_que_ya_no_existen():
    names = {name for _, name, _ in VIEWS}
    assert set(PUBLIC_VIEWS) | set(LOGIN_ONLY_VIEWS) <= names
