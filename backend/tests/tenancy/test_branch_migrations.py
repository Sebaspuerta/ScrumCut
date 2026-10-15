"""Migraciones de S1 con datos existentes, hacia adelante y en reversa (docs/sedes.md).

Cada prueba lleva la base al estado anterior, crea datos con los modelos históricos,
migra hacia adelante y revisa, y luego hace la reversa. El fixture vuelve siempre a las
últimas migraciones, aunque la prueba falle, para no dejar la base de pruebas a medias.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from tests.rls_support import postgres_only

pytestmark = [pytest.mark.django_db(transaction=True), postgres_only]

TENANCY_BEFORE = [("tenancy", "0003_order_number_and_credit_limit")]
TENANCY_AFTER = [("tenancy", "0005_main_branch_and_plan")]
STAFF_BEFORE = [("staff", "0001_initial")]
STAFF_AFTER = [("staff", "0004_remove_barber_branch")]
RECEIVABLES_BEFORE = [("receivables", "0001_initial")]
RECEIVABLES_AFTER = [("receivables", "0004_origin_branch_required")]


def _migrate(targets):
    """Migra a `targets` y devuelve los modelos históricos de todo lo aplicado (no solo de `targets`)."""
    MigrationExecutor(connection).migrate(targets)
    loader = MigrationExecutor(connection).loader
    return loader.project_state(tuple(loader.applied_migrations)).apps


@pytest.fixture
def back_to_latest():
    yield
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _shop(apps, slug: str):
    return apps.get_model("tenancy", "Barbershop").objects.create(trade_name=slug, slug=slug)


def _branch(apps, shop, name: str, *, active: bool = True):
    return apps.get_model("tenancy", "Branch").objects.create(barbershop=shop, name=name, is_active=active)


def test_la_sede_principal_y_el_limite_del_plan_se_migran(back_to_latest):
    apps = _migrate(TENANCY_BEFORE)
    empty = _shop(apps, "sin-sedes")
    busy = _shop(apps, "tres-sedes")
    for name, active in (("Centro", True), ("Norte", True), ("Vieja", False)):
        _branch(apps, busy, name, active=active)

    apps = _migrate(TENANCY_AFTER)
    shops, branches = apps.get_model("tenancy", "Barbershop").objects, apps.get_model("tenancy", "Branch").objects

    assert list(branches.filter(barbershop_id=empty.pk).values_list("name", flat=True)) == ["Sede principal"]
    assert shops.get(pk=empty.pk).max_branches == 1
    assert shops.get(pk=busy.pk).max_branches == 2  # cuenta solo las activas
    assert branches.filter(barbershop_id=busy.pk).count() == 3

    _migrate(TENANCY_BEFORE)  # la reversa quita la columna y conserva las sedes
    assert "max_branches" not in _columns("tenancy_barbershop")


def test_barber_branch_pasa_a_barber_branch_y_los_nulos_a_todas_las_activas(back_to_latest):
    apps = _migrate(STAFF_BEFORE)
    barbers = apps.get_model("staff", "Barber").objects
    shop = _shop(apps, "a")
    centro, norte, old = (
        _branch(apps, shop, "Centro"),
        _branch(apps, shop, "Norte"),
        _branch(apps, shop, "Vieja", active=False),
    )
    own = barbers.create(barbershop=shop, display_name="Ana", branch=norte)
    anywhere = barbers.create(barbershop=shop, display_name="Beto")
    retired = barbers.create(barbershop=shop, display_name="Caro", branch=old)

    apps = _migrate(STAFF_AFTER)
    links = apps.get_model("staff", "BarberBranch").objects

    def branches_of(barber):
        return set(links.filter(barber_id=barber.pk).values_list("branch_id", flat=True))

    assert branches_of(own) == {norte.pk}
    assert branches_of(anywhere) == {centro.pk, norte.pk}  # la sede nula: todas las activas
    assert branches_of(retired) == {old.pk}

    barbers = _migrate(STAFF_BEFORE).get_model("staff", "Barber").objects
    assert dict(barbers.values_list("display_name", "branch_id")) == {
        "Ana": norte.pk,
        "Beto": None,  # con varias sedes no hay una sola que devolver
        "Caro": old.pk,
    }


def test_el_fiado_toma_la_sede_de_su_comanda_o_la_sede_principal(back_to_latest):
    apps = _migrate(RECEIVABLES_BEFORE)
    shop = _shop(apps, "a")
    main, norte = _branch(apps, shop, "Principal"), _branch(apps, shop, "Norte")
    user = apps.get_model("accounts", "User").objects.create(email="cajero@a.test", password="!")
    client = apps.get_model("clients", "Client").objects.create(
        barbershop=shop, full_name="Laura", data_consent_at=timezone.now() - timedelta(days=1), data_policy_version="1"
    )
    order = apps.get_model("sales", "Order").objects.create(barbershop=shop, number=1, branch=norte, created_by=user)
    debts = apps.get_model("receivables", "Receivable").objects
    debt = {
        "barbershop": shop,
        "client": client,
        "total": Decimal("1000"),
        "balance": Decimal("1000"),
        "created_by": user,
    }
    from_order = debts.create(order=order, **debt)
    manual = debts.create(**debt)

    debts = _migrate(RECEIVABLES_AFTER).get_model("receivables", "Receivable").objects

    assert debts.get(pk=from_order.pk).origin_branch_id == norte.pk
    assert debts.get(pk=manual.pk).origin_branch_id == main.pk  # la más antigua

    _migrate(RECEIVABLES_BEFORE)
    assert "origin_branch_id" not in _columns("receivables_receivable")


def _columns(table: str) -> set[str]:
    with connection.cursor() as cursor:
        return {column.name for column in connection.introspection.get_table_description(cursor, table)}
