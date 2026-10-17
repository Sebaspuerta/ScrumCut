"""Quién ve y exporta reportes (regla 5) y aislamiento entre barberías."""

import pytest
from django.core.exceptions import PermissionDenied

from apps.core.tenant_context import tenant_context
from apps.reports.excel.builder import build_business_report
from apps.reports.selectors import income, sales
from apps.reports.selectors.dashboard import dashboard_summary
from apps.reports.selectors.receivables import receivables_report
from apps.tenancy.branch_scope import resolve_scope
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.reports.helpers import sell

pytestmark = pytest.mark.django_db

READERS = [Role.OWNER, Role.ADMIN, Role.CASHIER, Role.VIEWER]


@pytest.mark.parametrize("role", READERS)
def test_ven_reportes_quienes_tienen_reportes_ver(world, member, role):
    existing = {Role.OWNER: world.owner, Role.CASHIER: world.cashier}
    reader = existing.get(role) or member(role, world.shop)
    assert sum(day["orders"] for day in sales.sales_by_period(reader, scope=scope_of(reader))) == 0
    assert dashboard_summary(reader, scope=scope_of(reader))["orders_open"] == 0


def test_el_barbero_no_ve_reportes(world):
    scope = resolve_scope(world.ana_login)  # el permiso se revisa antes que el alcance
    for report in (sales.sales_by_period, sales.sales_by_barber, income.income_statement, receivables_report):
        with pytest.raises(PermissionDenied):
            report(world.ana_login, scope=scope)


@pytest.mark.parametrize("role", [Role.CASHIER, Role.VIEWER, Role.BARBER])
def test_solo_dueno_y_administrador_exportan(world, member, role):
    other = member(role, world.shop, email=f"otro-{role}@a.test")
    with pytest.raises(PermissionDenied):
        build_business_report(other, scope=resolve_scope(other))
    admin = member(Role.ADMIN, world.shop)
    assert build_business_report(admin, scope=scope_of(admin))


def test_cada_barberia_ve_solo_sus_ventas(world, member, other_shop):
    sell(world, world.ana, service=world.corte)
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        assert sum(day["orders"] for day in sales.sales_by_period(theirs, scope=scope_of(theirs))) == 0
        assert income.income_statement(theirs, scope=scope_of(theirs))["gross_sales"] == 0
        assert dashboard_summary(theirs, scope=scope_of(theirs))["open_cash_sessions"] == []
        with pytest.raises(PermissionDenied):
            sales.sales_by_period(world.owner, scope=scope_of(world.owner))
    assert sum(day["orders"] for day in sales.sales_by_period(world.owner, scope=scope_of(world.owner))) == 1
