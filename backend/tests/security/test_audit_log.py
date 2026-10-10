"""La auditoría es solo-agregar y PostgreSQL la aísla por barbería, salvo los eventos de plataforma."""

import pytest

from apps.audit.models import record
from tests.rls_support import become_app_role, insert_as, insert_is_rejected, postgres_only, visible_barbershops

pytestmark = pytest.mark.django_db

TABLE = "audit_auditlog"
INSERT_EVENT = (
    "INSERT INTO audit_auditlog (barbershop_id, action, entity, entity_id, user_agent, created_at) "
    "VALUES (%s, 'prueba', 'test', '', '', now())"
)


def test_la_auditoria_no_se_modifica_ni_se_borra():
    entry = record(action="prueba", entity="test")
    entry.action = "alterada"
    with pytest.raises(PermissionError):
        entry.save()
    with pytest.raises(PermissionError):
        entry.delete()


@pytest.fixture
def two_shops_and_platform(make_shop):
    a, b = make_shop("a"), make_shop("b")
    for barbershop in (a, b, None):
        record(action="prueba", entity="test", barbershop=barbershop)
    become_app_role(TABLE)
    return a, b


@postgres_only
def test_una_barberia_no_lee_ni_escribe_la_auditoria_de_otra(two_shops_and_platform):
    a, b = two_shops_and_platform
    assert visible_barbershops(TABLE, a.pk) == [a.pk]
    assert visible_barbershops(TABLE, b.pk) == [b.pk]
    insert_as(a.pk, INSERT_EVENT, [a.pk])  # control positivo
    assert insert_is_rejected(a.pk, INSERT_EVENT, [b.pk])


@postgres_only
def test_los_eventos_de_plataforma_se_escriben_y_leen_sin_barberia_activa(two_shops_and_platform):
    insert_as(None, INSERT_EVENT, [None])
    assert visible_barbershops(TABLE, None) == [None, None]
