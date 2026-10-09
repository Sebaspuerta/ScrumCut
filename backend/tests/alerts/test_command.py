"""Comando generar_alertas: recorre las barberías operativas, cada una en su tenant_context."""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.alerts.models import Alert
from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Barbershop
from apps.tenancy.roles import Role
from tests.alerts.helpers import make_product

pytestmark = pytest.mark.django_db


def test_el_comando_recorre_las_barberias_operativas(member, make_shop):
    shops = [make_shop("norte"), make_shop("sur"), make_shop("cerrada")]
    for shop in shops:
        with tenant_context(shop.pk):
            make_product(member(Role.OWNER, shop), "Cera")
    Barbershop.objects.filter(pk=shops[2].pk).update(status=Barbershop.Status.SUSPENDED)

    out = StringIO()
    call_command("generar_alertas", stdout=out)
    call_command("generar_alertas", stdout=StringIO())  # idempotente también por comando

    for shop, expected in zip(shops, (1, 1, 0), strict=True):
        with tenant_context(shop.pk):
            assert Alert.objects.count() == expected
    assert "norte" in out.getvalue() and "sur" in out.getvalue() and "cerrada" not in out.getvalue()
