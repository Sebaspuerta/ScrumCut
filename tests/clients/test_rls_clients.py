"""Barrera 2 para clientes: PostgreSQL aísla `clients_client` con SQL directo.

Mismo esquema que tests/test_rls_postgres.py, con control positivo: el INSERT en
la barbería propia funciona, así que el rechazo en la ajena se debe a RLS.
"""

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.clients.models import Client
from apps.core.tenant_context import tenant_context

pytestmark = [
    pytest.mark.django_db(transaction=False),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="RLS solo existe en PostgreSQL"),
]

PROBE_ROLE = "scrumcut_rls_probe"

INSERT_CLIENT = (
    "INSERT INTO clients_client "
    "(public_id, created_at, updated_at, barbershop_id, full_name, phone, email, notes, "
    "document_number_encrypted, document_hash, data_consent_at, data_policy_version, name_key) "
    "VALUES (gen_random_uuid(), now(), now(), %s, %s, '', '', '', '', '', now(), '2026-10', '')"
)


@pytest.fixture
def two_shops_with_clients(make_shop):
    a, b = make_shop("a"), make_shop("b")
    for shop, name in ((a, "Cliente A"), (b, "Cliente B")):
        with tenant_context(shop.pk):
            Client.objects.create(full_name=name, data_consent_at=timezone.now(), data_policy_version="2026-10")
    return a, b


@pytest.fixture
def as_app_role(two_shops_with_clients):
    with connection.cursor() as cursor:
        cursor.execute(f"DROP ROLE IF EXISTS {PROBE_ROLE}")
        cursor.execute(f"CREATE ROLE {PROBE_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        cursor.execute(f"GRANT SELECT, INSERT ON clients_client TO {PROBE_ROLE}")
        cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {PROBE_ROLE}")
        cursor.execute(f"SET LOCAL ROLE {PROBE_ROLE}")
    return two_shops_with_clients


def _fix_barbershop(cursor, barbershop_id: int | None) -> None:
    value = "" if barbershop_id is None else str(barbershop_id)
    cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [value])


def _names_visible_with(barbershop_id: int | None) -> list[str]:
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, barbershop_id)
        cursor.execute("SELECT full_name FROM clients_client ORDER BY full_name")
        return [row[0] for row in cursor.fetchall()]


def test_cada_barberia_ve_solo_sus_clientes(as_app_role):
    a, b = as_app_role
    assert _names_visible_with(a.pk) == ["Cliente A"]
    assert _names_visible_with(b.pk) == ["Cliente B"]


def test_sin_barberia_fijada_no_hay_clientes(as_app_role):
    assert _names_visible_with(None) == []


def test_se_inserta_en_la_barberia_fijada(as_app_role):
    a, _ = as_app_role
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, a.pk)
        cursor.execute(INSERT_CLIENT, [a.pk, "Propio"])
    assert _names_visible_with(a.pk) == ["Cliente A", "Propio"]


def test_no_se_inserta_un_cliente_en_otra_barberia(as_app_role):
    a, b = as_app_role
    with connection.cursor() as cursor:
        _fix_barbershop(cursor, a.pk)
        with pytest.raises(DatabaseError), transaction.atomic():
            cursor.execute(INSERT_CLIENT, [b.pk, "Intruso"])
