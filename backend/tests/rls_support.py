"""Apoyo para las pruebas de Row-Level Security (barrera 2).

Las consultas son SQL directo con un rol sin privilegios, porque un superusuario
ignora RLS. Cada tabla se prueba con un control positivo (insertar en la barbería
fijada funciona) para que el rechazo en la ajena solo pueda deberse a RLS.
"""

import pytest
from django.db import DatabaseError, connection, transaction

PROBE_ROLE = "scrumcut_rls_probe"

postgres_only = pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL")


def _assume_probe_role(grant: str) -> None:
    """Crea el rol de prueba con `grant` y lo asume hasta el fin de la transacción."""
    with connection.cursor() as cursor:
        cursor.execute(f"DROP ROLE IF EXISTS {PROBE_ROLE}")
        cursor.execute(f"CREATE ROLE {PROBE_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        cursor.execute(f"{grant} TO {PROBE_ROLE}")
        cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {PROBE_ROLE}")
        cursor.execute(f"SET LOCAL ROLE {PROBE_ROLE}")


def become_app_role(*tables: str) -> None:
    """SELECT e INSERT solo en `tables`: para probar la política de una tabla con SQL directo."""
    _assume_probe_role(f"GRANT SELECT, INSERT ON {', '.join(tables)}")


def become_production_role() -> None:
    """Lectura y escritura en todas las tablas, sin superusuario: como la app en producción."""
    _assume_probe_role("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public")


def back_to_test_role() -> None:
    """Vuelve al rol de las pruebas para verificar el resultado sin el filtro de RLS."""
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")


def _fix_barbershop(cursor, barbershop_id: int | None) -> None:
    value = "" if barbershop_id is None else str(barbershop_id)
    cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [value])


def visible_barbershops(table: str, barbershop_id: int | None) -> list[int]:
    """`barbershop_id` de cada fila que la base deja ver con esa barbería fijada."""
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, barbershop_id)
        cursor.execute(f"SELECT barbershop_id FROM {table} ORDER BY id")  # noqa: S608 — nombre de tabla fijo de la prueba
        return [row[0] for row in cursor.fetchall()]


def insert_as(barbershop_id: int, sql: str, params: list) -> None:
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, barbershop_id)
        cursor.execute(sql, params)


def insert_is_rejected(barbershop_id: int, sql: str, params: list) -> bool:
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, barbershop_id)
        try:
            with transaction.atomic():
                cursor.execute(sql, params)
        except DatabaseError:
            return True
    return False
