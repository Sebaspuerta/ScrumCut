"""Punto 8: PostgreSQL aísla cada barbería con Row-Level Security, no una llave en el navegador.

Regla 3 de `AGENTS.md`: cada migración de una tabla de negocio termina con
`EnableTenantRLS`. Si alguien la olvida, la tabla queda abierta entre barberías y
nada más lo detectaría; estas pruebas leen el catálogo de PostgreSQL.
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

# Tablas con barbershop_id que no son de negocio, con su motivo.
WITHOUT_RLS = {
    "tenancy_membership": "Se lee antes de fijar la barbería activa: así se sabe a cuál entra el usuario.",
    "legal_acceptance": "La aceptación es de la persona; la barbería es opcional.",
}


def _rls_flags(table: str) -> tuple[bool, bool, int]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = %s", [table])
        enabled, forced = cursor.fetchone()
        cursor.execute(
            "SELECT count(*) FROM pg_policies WHERE tablename = %s AND policyname = 'tenant_isolation'", [table]
        )
        return enabled, forced, cursor.fetchone()[0]


def test_hay_tablas_de_negocio_que_revisar():
    assert len(TENANT_TABLES) >= 15


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_la_tabla_tiene_rls_forzado_y_politica_por_barberia(table):
    assert _rls_flags(table) == (True, True, 1), f"{table} no tiene RLS completo"


def test_toda_tabla_con_barbershop_id_tiene_rls_o_un_motivo_para_no_tenerlo():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name = 'barbershop_id'"
        )
        tables = {row[0] for row in cursor.fetchall()}
    unprotected = sorted(t for t in tables - set(WITHOUT_RLS) if _rls_flags(t)[:2] != (True, True))
    assert unprotected == []
    assert set(WITHOUT_RLS) <= tables  # una excepción que ya no existe se quita de la lista
