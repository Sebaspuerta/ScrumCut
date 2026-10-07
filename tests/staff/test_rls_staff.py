"""Barrera 2 para personal: PostgreSQL aísla `staff_barber` y `staff_commissionrule`.

Mismo esquema que tests/test_rls_postgres.py: un rol sin privilegios, porque un
superusuario ignora RLS. Cada tabla tiene un control positivo (el INSERT en la
barbería propia funciona), así que el rechazo en la ajena se debe a RLS.
"""

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.core.tenant_context import tenant_context
from apps.staff.models import Barber, CommissionRule

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

PROBE_ROLE = "scrumcut_rls_probe"

INSERT_BARBER = (
    "INSERT INTO staff_barber "
    "(public_id, created_at, updated_at, barbershop_id, display_name, alias, phone, is_active, notes) "
    "VALUES (gen_random_uuid(), now(), now(), %s, %s, '', '', true, '')"
)
INSERT_RULE = (
    "INSERT INTO staff_commissionrule "
    "(public_id, created_at, updated_at, barbershop_id, barber_id, commission_type, value, valid_from) "
    "VALUES (gen_random_uuid(), now(), now(), %s, %s, 'percentage', 10, now())"
)


@pytest.fixture
def two_shops_with_staff(make_shop):
    a, b = make_shop("a"), make_shop("b")
    barbers = {}
    for shop, name in ((a, "Ana"), (b, "Beto")):
        with tenant_context(shop.pk):
            barber = Barber.objects.create(display_name=name)
            CommissionRule.objects.create(
                barber=barber, commission_type="percentage", value=40, valid_from=timezone.now()
            )
            barbers[shop.pk] = barber
    return a, b, barbers


@pytest.fixture
def as_app_role(two_shops_with_staff):
    with connection.cursor() as cursor:
        cursor.execute(f"DROP ROLE IF EXISTS {PROBE_ROLE}")
        cursor.execute(f"CREATE ROLE {PROBE_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        cursor.execute(f"GRANT SELECT, INSERT ON staff_barber, staff_commissionrule TO {PROBE_ROLE}")
        cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {PROBE_ROLE}")
        cursor.execute(f"SET LOCAL ROLE {PROBE_ROLE}")
    return two_shops_with_staff


def _fix_barbershop(cursor, barbershop_id: int | None) -> None:
    value = "" if barbershop_id is None else str(barbershop_id)
    cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [value])


def _visible(barbershop_id: int | None) -> tuple[list[str], list[int]]:
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, barbershop_id)
        cursor.execute("SELECT display_name FROM staff_barber ORDER BY display_name")
        names = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT barber_id FROM staff_commissionrule ORDER BY id")
        rule_barbers = [row[0] for row in cursor.fetchall()]
    return names, rule_barbers


def test_cada_barberia_ve_solo_su_personal_y_sus_reglas(as_app_role):
    a, b, barbers = as_app_role
    assert _visible(a.pk) == (["Ana"], [barbers[a.pk].pk])
    assert _visible(b.pk) == (["Beto"], [barbers[b.pk].pk])


def test_sin_barberia_fijada_no_hay_filas(as_app_role):
    assert _visible(None) == ([], [])


def test_se_inserta_en_la_barberia_fijada(as_app_role):
    a, _, barbers = as_app_role
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, a.pk)
        cursor.execute(INSERT_BARBER, [a.pk, "Propio"])
        cursor.execute(INSERT_RULE, [a.pk, barbers[a.pk].pk])
    names, rule_barbers = _visible(a.pk)
    assert names == ["Ana", "Propio"]
    assert len(rule_barbers) == 2


@pytest.mark.parametrize("table", ["barber", "rule"])
def test_no_se_inserta_en_otra_barberia(as_app_role, table):
    a, b, barbers = as_app_role
    statement, params = (
        (INSERT_BARBER, [b.pk, "Intruso"]) if table == "barber" else (INSERT_RULE, [b.pk, barbers[b.pk].pk])
    )
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, a.pk)
        with pytest.raises(DatabaseError), transaction.atomic():
            cursor.execute(statement, params)
