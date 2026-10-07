"""Fiados (app receivables). Usan el fixture `world` de tests/conftest.py: caja abierta y cliente."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.cash import services as cash
from apps.cash.models import CashMovement, MovementKind
from apps.clients import services as clients
from apps.core.tenant_context import tenant_context
from apps.receivables import selectors, services
from apps.receivables.models import Receivable, ReceivablePayment, ReceivableStatus
from apps.tenancy.models import BarbershopSettings
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db

D = Decimal


def _debt(w, total="30000", **kwargs):
    return services.create_manual(w.cashier, w.laura.public_id, D(total), **kwargs)


def _pay(w, debt, amount, method="efectivo"):
    return services.add_payment(w.cashier, debt.public_id, D(amount), method, w.branch.public_id)


def _code(excinfo) -> str:
    return excinfo.value.error_list[0].code


def test_fiado_manual(world):
    debt = _debt(world, notes="Productos fiados")
    assert (debt.total, debt.balance, debt.status, debt.order) == (
        D("30000"),
        D("30000"),
        ReceivableStatus.PENDING,
        None,
    )
    with pytest.raises(ValidationError):
        _debt(world, total="0")


def test_no_se_fia_a_un_cliente_anonimizado(world):
    clients.anonymize_client(world.owner, world.laura.public_id)
    with pytest.raises(ValidationError):
        _debt(world)


def test_abono_parcial_y_abono_que_salda(world):
    debt = _debt(world)
    payment = _pay(world, debt, "10000", method="nequi")
    debt.refresh_from_db()
    assert (debt.balance, debt.status) == (D("20000"), ReceivableStatus.PENDING)
    movement = payment.cash_movement
    assert (movement.kind, movement.payment_method, movement.amount, movement.session) == (
        MovementKind.RECEIVABLE_PAYMENT,
        "nequi",
        D("10000"),
        world.session,
    )

    _pay(world, debt, "20000")
    debt.refresh_from_db()
    assert (debt.balance, debt.status) == (D("0"), ReceivableStatus.PAID)
    assert selectors.client_balance(world.laura) == D("0")


@pytest.mark.parametrize("case", ["mayor_al_saldo", "pagado", "anulado", "sin_caja", "metodo_apagado", "cero"])
def test_abonos_rechazados(world, case):
    debt = _debt(world)
    amount = "1000"
    if case == "mayor_al_saldo":
        amount = "30001"
    elif case == "pagado":
        _pay(world, debt, "30000")
    elif case == "anulado":
        services.cancel_receivable(world.owner, debt.public_id, "Error de digitación")
    elif case == "sin_caja":
        cash.close_session(world.cashier, world.session.public_id, D("50000"))
    elif case == "metodo_apagado":
        settings = BarbershopSettings.objects.get()
        settings.enabled_payment_methods = ["nequi"]
        settings.save()
    else:
        amount = "0"
    payments_before = ReceivablePayment.objects.count()

    with pytest.raises(ValidationError):
        _pay(world, debt, amount)
    assert ReceivablePayment.objects.count() == payments_before


def test_anular_un_fiado_exige_permiso_y_que_no_tenga_abonos(world):
    debt = _debt(world)
    with pytest.raises(PermissionDenied):
        services.cancel_receivable(world.cashier, debt.public_id, "Error")
    with pytest.raises(ValidationError):
        services.cancel_receivable(world.owner, debt.public_id, "  ")

    paid = _debt(world, total="5000")
    _pay(world, paid, "1000")
    with pytest.raises(ValidationError) as excinfo:
        services.cancel_receivable(world.owner, paid.public_id, "Error")
    assert _code(excinfo) == "has_payments"

    cancelled = services.cancel_receivable(world.owner, debt.public_id, "Error de digitación")
    assert (cancelled.status, cancelled.balance) == (ReceivableStatus.CANCELLED, D("0"))


def test_limite_de_credito_en_fiados_manuales(world):
    settings = BarbershopSettings.objects.get()
    settings.max_credit_per_client = D("40000")
    settings.save()
    _debt(world, total="30000")
    with pytest.raises(ValidationError) as excinfo:
        _debt(world, total="10001")
    assert _code(excinfo) == "credit_limit"
    assert _debt(world, total="10000").pk


def test_vencidos_por_fecha_sin_escrituras_en_la_lectura(world):
    today = selectors.local_today(world.cashier)
    overdue = _debt(world, total="10000", due_date=today - timedelta(days=1))
    _debt(world, total="20000", due_date=today + timedelta(days=10))
    _debt(world, total="5000")

    with CaptureQueriesContext(connection) as queries:
        summary = selectors.receivables_summary(world.cashier)
    assert not [q for q in queries.captured_queries if q["sql"].lstrip().upper().startswith(("UPDATE", "INSERT"))]
    assert summary == {
        "pending_count": 3,
        "pending_balance": D("35000"),
        "overdue_count": 1,
        "overdue_balance": D("10000"),
    }
    overdue.refresh_from_db()
    assert overdue.status == ReceivableStatus.PENDING  # leer no cambia el estado

    assert services.mark_overdue(today) == 1
    overdue.refresh_from_db()
    assert overdue.status == ReceivableStatus.OVERDUE
    _pay(world, overdue, "10000")  # un vencido también se abona
    overdue.refresh_from_db()
    assert overdue.status == ReceivableStatus.PAID


def test_lista_y_permisos_de_lectura(world, member):
    debt = _debt(world)
    assert list(selectors.list_receivables(world.cashier, client=world.laura.public_id)) == [debt]
    assert list(selectors.list_receivables(world.cashier, status=ReceivableStatus.PAID)) == []
    with pytest.raises(PermissionDenied):
        selectors.list_receivables(world.ana_login)
    viewer = member(Role.VIEWER, world.shop)
    assert selectors.get_receivable(viewer, debt.public_id) == debt
    with pytest.raises(PermissionDenied):
        services.create_manual(viewer, world.laura.public_id, D("1000"))


def test_otra_barberia_no_ve_ni_abona_fiados_ajenos(world, member, other_shop):
    debt = _debt(world)
    with tenant_context(other_shop.pk):
        outsider = member(Role.OWNER, other_shop)
        assert list(selectors.list_receivables(outsider)) == []
        with pytest.raises(Receivable.DoesNotExist):
            selectors.get_receivable(outsider, debt.public_id)
    assert not CashMovement.objects.filter(kind=MovementKind.RECEIVABLE_PAYMENT).exists()
