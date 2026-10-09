"""Toda tabla de negocio tiene Row-Level Security activado, forzado y con su política.

Regla 3 de `CLAUDE.md`: cada migración de una tabla de negocio termina con
`EnableTenantRLS`. Si alguien la olvida, la tabla queda abierta entre barberías y
nada más lo detectaría; esta prueba lee el catálogo de PostgreSQL.
"""

import pytest
from django.apps import apps
from django.db import connection

from apps.core.models import TenantScopedModel

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

TENANT_TABLES = sorted(
    model._meta.db_table
    for model in apps.get_models()
    if issubclass(model, TenantScopedModel) and not model._meta.proxy and model._meta.managed
)


def test_hay_tablas_de_negocio_que_revisar():
    assert len(TENANT_TABLES) >= 15


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_la_tabla_tiene_rls_forzado_y_politica_por_barberia(table):
    with connection.cursor() as cursor:
        cursor.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = %s", [table])
        enabled, forced = cursor.fetchone()
        cursor.execute(
            "SELECT count(*) FROM pg_policies WHERE tablename = %s AND policyname = 'tenant_isolation'", [table]
        )
        policies = cursor.fetchone()[0]
    assert (enabled, forced, policies) == (True, True, 1), f"{table} no tiene RLS completo"
