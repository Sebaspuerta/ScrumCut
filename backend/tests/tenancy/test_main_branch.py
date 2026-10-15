"""Toda barbería nace con su Sede principal, en la misma transacción (decisión 12 de docs/sedes.md)."""

from unittest import mock

import pytest
from django.db import DatabaseError

from apps.core.tenant_context import tenant_context
from apps.tenancy.models import MAIN_BRANCH_NAME, Barbershop, BarbershopSettings, Branch

pytestmark = pytest.mark.django_db


def test_una_barberia_nueva_tiene_su_sede_principal_y_un_plan_de_una_sede(make_shop):
    shop = make_shop("nueva")
    with tenant_context(shop.pk):
        assert list(Branch.objects.values_list("name", "is_active")) == [(MAIN_BRANCH_NAME, True)]
    assert shop.max_branches == 1


def test_si_la_sede_no_se_crea_tampoco_queda_la_barberia(db):
    with (
        mock.patch.object(Branch.objects, "create", side_effect=DatabaseError("falla simulada")),
        pytest.raises(DatabaseError),
    ):
        Barbershop.objects.create(trade_name="A medias", slug="a-medias")

    assert not Barbershop.objects.filter(slug="a-medias").exists()
    assert not BarbershopSettings.unscoped.filter(barbershop__slug="a-medias").exists()  # prueba de plataforma
