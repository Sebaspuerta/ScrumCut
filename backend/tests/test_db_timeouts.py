"""La conexión de pruebas lleva los límites de config/settings/test.py: una espera nunca cuelga la suite."""

import pytest
from django.db import connection

from tests.rls_support import postgres_only

pytestmark = [pytest.mark.django_db, postgres_only]


def _show(statement: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute(statement)
        return cursor.fetchone()[0]


def test_la_conexion_de_pruebas_corta_esperas_por_bloqueo_y_sentencias_largas():
    assert _show("SHOW lock_timeout") == "10s"
    assert _show("SHOW statement_timeout") == "30s"
