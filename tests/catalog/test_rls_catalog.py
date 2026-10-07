"""Barrera 2 para el catálogo: PostgreSQL aísla `catalog_service` con SQL directo.

Mismo esquema que tests/test_rls_postgres.py: un rol sin privilegios, porque un
superusuario ignora RLS.
"""

import pytest
from django.db import DatabaseError, connection, transaction

from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

PROBE_ROLE = "scrumcut_rls_probe"


@pytest.fixture
def two_shops_with_services(make_shop):
    a, b = make_shop("a"), make_shop("b")
    with tenant_context(a.pk):
        Service.objects.create(name="Corte A", price=20000, duration_minutes=30)
    with tenant_context(b.pk):
        Service.objects.create(name="Corte B", price=25000, duration_minutes=40)
    return a, b


@pytest.fixture
def as_app_role(two_shops_with_services):
    with connection.cursor() as cursor:
        cursor.execute(f"DROP ROLE IF EXISTS {PROBE_ROLE}")
        cursor.execute(f"CREATE ROLE {PROBE_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        cursor.execute(f"GRANT SELECT, INSERT ON catalog_service TO {PROBE_ROLE}")
        cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {PROBE_ROLE}")
        cursor.execute(f"SET LOCAL ROLE {PROBE_ROLE}")
    return two_shops_with_services


def _names_visible_with(barbershop_id: int | None) -> list[str]:
    with connection.cursor() as cursor:
        value = "" if barbershop_id is None else str(barbershop_id)
        cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [value])
        cursor.execute("SELECT name FROM catalog_service ORDER BY name")
        return [row[0] for row in cursor.fetchall()]


def test_cada_barberia_ve_solo_sus_servicios_en_sql_directo(as_app_role):
    a, b = as_app_role
    assert _names_visible_with(a.pk) == ["Corte A"]
    assert _names_visible_with(b.pk) == ["Corte B"]


def test_sin_barberia_fijada_no_hay_servicios(as_app_role):
    assert _names_visible_with(None) == []


_INSERT = (
    "INSERT INTO catalog_service "
    "(public_id, created_at, updated_at, barbershop_id, name, description, price, duration_minutes, is_active) "
    "VALUES (gen_random_uuid(), now(), now(), %s, %s, '', 1000, 30, true)"
)


def test_se_inserta_en_la_barberia_fijada(as_app_role):
    """Control: el mismo INSERT funciona en la barbería propia, así que el rechazo de abajo es RLS."""
    a, _ = as_app_role
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [str(a.pk)])
        cursor.execute(_INSERT, [a.pk, "Propio"])
    assert _names_visible_with(a.pk) == ["Corte A", "Propio"]


def test_no_se_puede_insertar_un_servicio_en_otra_barberia(as_app_role):
    a, b = as_app_role
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [str(a.pk)])
        with pytest.raises(DatabaseError), transaction.atomic():
            cursor.execute(_INSERT, [b.pk, "Intruso"])
