"""receivables.0005: la referencia del abono se agrega sin tocar los abonos que ya existen, y la reversa la quita."""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core.tenant_context import tenant_context
from apps.receivables import services as receivables
from apps.receivables.models import ReceivablePayment
from tests.conftest import scope_of
from tests.rls_support import postgres_only

# slow: en local se pueden saltar con -m "not slow"; CI las corre siempre.
pytestmark = [pytest.mark.django_db(transaction=True), postgres_only, pytest.mark.slow]

BEFORE = [("receivables", "0004_origin_branch_required")]
AFTER = [("receivables", "0005_payment_reference")]


@pytest.fixture
def back_to_latest():
    yield
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _columns() -> set[str]:
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(cursor, "receivables_receivablepayment")
        }


def test_un_abono_que_ya_existe_queda_igual_y_sin_referencia(world, back_to_latest):
    scope = scope_of(world.owner, world.branch)
    debt = receivables.create_manual(world.owner, world.laura.public_id, scope=scope, total=Decimal("25000"))
    receivables.add_payment(world.owner, debt.public_id, scope=scope, amount=Decimal("5000"), method="nequi")
    before = ReceivablePayment.objects.values("pk", "amount", "method", "cash_movement_id", "created_at").get()

    MigrationExecutor(connection).migrate(BEFORE)
    assert "reference" not in _columns()
    MigrationExecutor(connection).migrate(AFTER)

    with tenant_context(world.shop.pk):
        after = ReceivablePayment.objects.values(*before, "reference").get()
    assert after == {**before, "reference": ""}
