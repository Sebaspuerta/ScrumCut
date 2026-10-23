"""El nivel en SQL (`level_expression`, para filtrar y contar la lista) dice lo mismo que `client_status`."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db.models import DateTimeField, DecimalField, IntegerField, Value
from django.utils import timezone

from apps.clients.board import level_expression
from apps.clients.models import Client
from apps.clients.selectors import client_status
from apps.tenancy.models import BarbershopSettings

pytestmark = pytest.mark.django_db

D = Decimal
NOW = timezone.now()
RECENT, OLD = NOW - timedelta(days=5), NOW - timedelta(days=200)

# (visitas, gasto total, última visita, deuda): cada umbral por debajo, justo en él y por encima.
CASES = [
    (0, D("0"), None, D("0")),
    (0, D("0"), None, D("1000")),
    (1, D("25000"), RECENT, D("0")),
    (2, D("50000"), RECENT, D("0")),
    (3, D("75000"), RECENT, D("0")),
    (9, D("200000"), RECENT, D("0")),
    (10, D("250000"), RECENT, D("0")),
    (1, D("999999999"), RECENT, D("0")),
    (5, D("125000"), OLD, D("0")),
    (5, D("125000"), OLD, D("5000")),
]


@pytest.mark.parametrize(("visits", "spent", "last_visit", "debt"), CASES)
def test_el_nivel_en_sql_coincide_con_la_regla(in_shop, visits, spent, last_visit, debt):
    Client.objects.create(full_name="Uno", data_consent_at=NOW, data_policy_version="1")
    settings = BarbershopSettings.objects.get()
    annotated = Client.objects.annotate(
        visits=Value(visits, IntegerField()),
        spent=Value(spent, DecimalField(max_digits=14, decimal_places=2)),
        last_visit=Value(last_visit, DateTimeField()),
        debt=Value(debt, DecimalField(max_digits=14, decimal_places=2)),
    ).annotate(level=level_expression(settings, now=NOW))

    assert annotated.get().level == client_status(visits, spent, last_visit, debt, settings, now=NOW)
