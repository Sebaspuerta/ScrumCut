"""Barrera 2: PostgreSQL bloquea filas de otra barbería aunque el código no filtre.

Las consultas aquí son SQL directo (sin managers de Django) y corren con un rol
sin privilegios, como el que usará la aplicación en producción. Un superusuario
ignora RLS, por eso la prueba cambia de rol.
"""

import pytest
from django.db import DatabaseError, connection, transaction

from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Branch

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

PROBE_ROLE = "scrumcut_rls_probe"


@pytest.fixture
def two_shops_with_branches(make_shop):
    a, b = make_shop("a"), make_shop("b")
    with tenant_context(a.pk):
        Branch.objects.create(name="Centro A")
    with tenant_context(b.pk):
        Branch.objects.create(name="Norte B")
    return a, b


@pytest.fixture
def as_app_role(two_shops_with_branches):
    """Cambia al rol sin privilegios dentro de la transacción de la prueba."""
    with connection.cursor() as cursor:
        cursor.execute(f"DROP ROLE IF EXISTS {PROBE_ROLE}")
        cursor.execute(f"CREATE ROLE {PROBE_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        cursor.execute(f"GRANT SELECT, INSERT ON tenancy_branch TO {PROBE_ROLE}")
        cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {PROBE_ROLE}")
        cursor.execute(f"SET LOCAL ROLE {PROBE_ROLE}")
    return two_shops_with_branches


def _names_visible_with(barbershop_id: int | None) -> list[str]:
    with connection.cursor() as cursor:
        value = "" if barbershop_id is None else str(barbershop_id)
        cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [value])
        cursor.execute("SELECT name FROM tenancy_branch ORDER BY name")
        return [row[0] for row in cursor.fetchall()]


def test_cada_barberia_ve_solo_sus_filas_en_sql_directo(as_app_role):
    a, b = as_app_role
    assert _names_visible_with(a.pk) == ["Centro A"]
    assert _names_visible_with(b.pk) == ["Norte B"]


def test_sin_barberia_fijada_la_base_no_devuelve_filas(as_app_role):
    assert _names_visible_with(None) == []


def test_no_se_puede_insertar_en_otra_barberia(as_app_role):
    a, b = as_app_role
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [str(a.pk)])
        with pytest.raises(DatabaseError), transaction.atomic():
            cursor.execute(
                "INSERT INTO tenancy_branch "
                "(public_id, created_at, updated_at, barbershop_id, name, address, phone, is_active) "
                "VALUES (gen_random_uuid(), now(), now(), %s, 'Intrusa', '', '', true)",
                [b.pk],
            )
