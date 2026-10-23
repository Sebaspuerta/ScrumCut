"""El número de consultas de `me` y `navigation` no crece con las sedes de la barbería."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.tenancy import services as tenancy
from apps.tenancy.models import Barbershop

pytestmark = pytest.mark.django_db

EXTRA_BRANCHES = ("Norte", "Sur", "Occidente")


def _queries(client, url_name: str) -> int:
    client.get(reverse(url_name))  # la primera petición puede guardar la sede en la sesión
    with CaptureQueriesContext(connection) as context:
        assert client.get(reverse(url_name)).status_code == 200
    return len(context.captured_queries)


@pytest.mark.parametrize("url_name", ["api_me", "api_navigation"])
def test_las_consultas_son_las_mismas_con_una_sede_que_con_cuatro(world, owner_client, url_name):
    with_one = _queries(owner_client, url_name)
    Barbershop.objects.filter(pk=world.shop.pk).update(max_branches=len(EXTRA_BRANCHES) + 1)
    world.owner.barbershop.refresh_from_db()
    for name in EXTRA_BRANCHES:
        tenancy.create_branch(world.owner, {"name": name})

    assert _queries(owner_client, url_name) == with_one
