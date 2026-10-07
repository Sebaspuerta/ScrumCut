from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.cash import selectors, services
from apps.cash.choices import PaymentMethod
from apps.cash.models import CashMovement, CashSession, Direction, MovementKind
from apps.core.tenant_context import tenant_context
from apps.tenancy.models import BarbershopSettings, Branch
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db

CASH, NEQUI, CARD = PaymentMethod.CASH, PaymentMethod.NEQUI, PaymentMethod.CARD


@pytest.fixture
def cashier(member, in_shop):
    return member(Role.CASHIER, in_shop)


@pytest.fixture
def branch(in_shop):
    return Branch.objects.create(name="Centro")


@pytest.fixture
def session(cashier, branch):
    return services.open_session(cashier, branch.public_id, Decimal("100000"))


def _money(session, kind, direction, method, amount, actor):
    return services.record_money(session, kind, direction, method, Decimal(amount), f"{kind} de prueba", actor)


# ── Apertura (regla 21, decisión 2, defecto 17) ──────────────────────────────


def test_abrir_caja_y_auditarla(cashier, branch):
    session = services.open_session(cashier, branch.public_id, Decimal("50000"), notes=" Turno mañana ")
    assert session.is_open
    assert (session.opened_by, session.opening_amount, session.notes) == (
        cashier.user,
        Decimal("50000"),
        "Turno mañana",
    )
    assert AuditLog.objects.get(action="caja.abrir").after["opening_amount"] == "50000.00"
    assert selectors.current_session(cashier, branch.public_id) == session


def test_una_sola_caja_abierta_por_sede(cashier, branch, session):
    with pytest.raises(ValidationError) as excinfo:
        services.open_session(cashier, branch.public_id, Decimal("0"))
    assert excinfo.value.error_list[0].code == "already_open"

    other_branch = Branch.objects.create(name="Norte")
    assert services.open_session(cashier, other_branch.public_id, Decimal("0")).is_open


def test_la_base_impide_dos_cajas_abiertas_aunque_se_salte_la_verificacion(cashier, branch, session, monkeypatch):
    """Simula la carrera: dos solicitudes pasan la verificación previa y full_clean a la vez."""
    monkeypatch.setattr(services, "_open_session_in", lambda branch: None)
    monkeypatch.setattr(CashSession, "full_clean", lambda self, *args, **kwargs: None)
    with pytest.raises(ValidationError) as excinfo:
        services.open_session(cashier, branch.public_id, Decimal("0"))
    assert excinfo.value.error_list[0].code == "already_open"
    assert CashSession.objects.filter(branch=branch, closed_at__isnull=True).count() == 1


def test_no_se_abre_con_base_negativa_ni_en_una_sede_ajena(cashier, member, other_shop):
    with pytest.raises(ValidationError):
        services.open_session(cashier, Branch.objects.create(name="Centro").public_id, Decimal("-1"))
    with tenant_context(other_shop.pk):
        foreign = Branch.objects.create(name="Ajena")
    with pytest.raises(ValidationError):
        services.open_session(cashier, foreign.public_id, Decimal("0"))


# ── Arqueo (regla 24, defectos 18, 20, 21, 23) ───────────────────────────────


def _full_day(session, actor):
    _money(session, MovementKind.SALE, Direction.IN, CASH, "50000", actor)
    _money(session, MovementKind.SALE, Direction.IN, NEQUI, "30000", actor)
    _money(session, MovementKind.SALE, Direction.IN, CARD, "20000", actor)
    _money(session, MovementKind.RECEIVABLE_PAYMENT, Direction.IN, CASH, "10000", actor)
    _money(session, MovementKind.MANUAL_INCOME, Direction.IN, CASH, "2000", actor)
    _money(session, MovementKind.EXPENSE, Direction.OUT, CASH, "15000", actor)
    _money(session, MovementKind.WITHDRAWAL, Direction.OUT, CASH, "40000", actor)
    _money(session, MovementKind.EXPENSE, Direction.OUT, NEQUI, "5000", actor)
    _money(session, MovementKind.ADJUSTMENT, Direction.OUT, CASH, "1000", actor)


# 100000 + 50000 + 10000 + 2000 − 15000 − 40000 − 1000 = 106000; Nequi y tarjeta no cuentan.
EXPECTED_CASH = Decimal("106000.00")


def test_el_resumen_y_el_cierre_calculan_el_mismo_efectivo(cashier, session):
    _full_day(session, cashier)

    summary = selectors.session_summary(cashier, session.public_id)
    assert summary["expected_cash"] == EXPECTED_CASH
    assert summary["by_method"][NEQUI] == {"in": Decimal("30000"), "out": Decimal("5000"), "net": Decimal("25000")}
    assert summary["by_method"][CARD]["net"] == Decimal("20000")
    assert summary["by_kind"][MovementKind.SALE] == Decimal("100000")
    assert summary["by_kind"][MovementKind.EXPENSE] == Decimal("20000")

    closed = services.close_session(cashier, session.public_id, Decimal("105000"), notes="Faltó un billete")
    assert (closed.expected_amount, closed.counted_amount, closed.difference) == (
        EXPECTED_CASH,
        Decimal("105000"),
        Decimal("-1000.00"),
    )
    assert closed.closed_by == cashier.user and not closed.is_open
    log = AuditLog.objects.get(action="caja.cerrar")
    assert (log.after["expected_amount"], log.after["difference"]) == ("106000.00", "-1000.00")
    assert selectors.session_summary(cashier, session.public_id)["difference"] == Decimal("-1000.00")


def test_una_caja_cerrada_no_recibe_movimientos_ni_se_cierra_dos_veces(cashier, branch, session):
    services.close_session(cashier, session.public_id, Decimal("100000"))
    with pytest.raises(ValidationError):
        services.close_session(cashier, session.public_id, Decimal("100000"))
    with pytest.raises(ValidationError):
        _money(session, MovementKind.SALE, Direction.IN, CASH, "1000", cashier)
    assert selectors.current_session(cashier, branch.public_id) is None
    assert services.open_session(cashier, branch.public_id, Decimal("0")).is_open


def test_el_contado_no_puede_ser_negativo(cashier, session):
    with pytest.raises(ValidationError):
        services.close_session(cashier, session.public_id, Decimal("-1"))
    session.refresh_from_db()
    assert session.is_open


# ── Movimientos (regla 25, decisión 4) ───────────────────────────────────────


def test_movimientos_manuales_toman_el_sentido_del_tipo(cashier, session):
    expense = services.register_manual_movement(
        cashier, session.public_id, MovementKind.EXPENSE, Decimal("8000"), CASH, "Café"
    )
    assert expense.direction == Direction.OUT
    adjustment = services.register_manual_movement(
        cashier, session.public_id, MovementKind.ADJUSTMENT, Decimal("500"), CASH, "Sobrante", direction=Direction.IN
    )
    assert adjustment.direction == Direction.IN


@pytest.mark.parametrize(
    ("kind", "amount", "description", "direction"),
    [
        (MovementKind.SALE, "1000", "Venta manual", None),
        (MovementKind.ADJUSTMENT, "1000", "Sin sentido", None),
        (MovementKind.EXPENSE, "0", "Monto cero", None),
        (MovementKind.EXPENSE, "1000", "   ", None),
    ],
    ids=["venta_no_es_manual", "ajuste_sin_sentido", "monto_cero", "sin_descripcion"],
)
def test_movimientos_manuales_invalidos(cashier, session, kind, amount, description, direction):
    with pytest.raises(ValidationError):
        services.register_manual_movement(
            cashier, session.public_id, kind, Decimal(amount), CASH, description, direction=direction
        )
    assert not CashMovement.objects.exists()


def test_tipo_y_sentido_deben_coincidir(cashier, session):
    with pytest.raises(ValidationError):
        _money(session, MovementKind.EXPENSE, Direction.IN, CASH, "1000", cashier)


def test_un_metodo_no_habilitado_se_rechaza(cashier, session):
    settings = BarbershopSettings.objects.get()
    settings.enabled_payment_methods = [CASH, CARD]
    settings.save()
    with pytest.raises(ValidationError):
        _money(session, MovementKind.SALE, Direction.IN, NEQUI, "1000", cashier)
    with pytest.raises(ValidationError):
        services.register_manual_movement(cashier, session.public_id, MovementKind.EXPENSE, Decimal("1"), NEQUI, "x")
    assert _money(session, MovementKind.SALE, Direction.IN, CARD, "1000", cashier).pk


def test_por_defecto_todos_los_metodos_estan_habilitados_y_nunca_ninguno(in_shop):
    settings = BarbershopSettings.objects.get()
    assert settings.enabled_payment_methods == list(PaymentMethod.values)
    settings.enabled_payment_methods = []
    with pytest.raises(ValidationError):
        settings.full_clean()


def test_un_movimiento_de_caja_no_se_edita_ni_se_borra(cashier, session):
    movement = _money(session, MovementKind.SALE, Direction.IN, CASH, "1000", cashier)
    movement.amount = Decimal("1")
    with pytest.raises(PermissionError):
        movement.save()
    with pytest.raises(PermissionError):
        movement.delete()
    with pytest.raises(PermissionError):
        CashMovement.objects.filter(pk=movement.pk).update(amount=Decimal("1"))
    with pytest.raises(PermissionError):
        CashMovement.objects.filter(pk=movement.pk).delete()


# ── Permisos ─────────────────────────────────────────────────────────────────


def test_el_barbero_no_maneja_caja(member, in_shop, branch, session):
    barber = member(Role.BARBER, in_shop)
    with pytest.raises(PermissionDenied):
        services.open_session(barber, Branch.objects.create(name="Norte").public_id, Decimal("0"))
    with pytest.raises(PermissionDenied):
        services.register_manual_movement(barber, session.public_id, MovementKind.EXPENSE, Decimal("1"), CASH, "x")
    with pytest.raises(PermissionDenied):
        services.close_session(barber, session.public_id, Decimal("0"))
    with pytest.raises(PermissionDenied):
        selectors.current_session(barber, branch.public_id)


def test_el_consultor_ve_pero_no_opera(member, in_shop, branch, session):
    viewer = member(Role.VIEWER, in_shop)
    assert selectors.current_session(viewer, branch.public_id) == session
    assert selectors.session_summary(viewer, session.public_id)["expected_cash"] == Decimal("100000")
    with pytest.raises(PermissionDenied):
        services.close_session(viewer, session.public_id, Decimal("0"))


def test_el_administrador_opera_la_caja(member, in_shop, branch):
    admin = member(Role.ADMIN, in_shop)
    session = services.open_session(admin, branch.public_id, Decimal("0"))
    services.register_manual_movement(admin, session.public_id, MovementKind.MANUAL_INCOME, Decimal("1"), CASH, "x")
    assert services.close_session(admin, session.public_id, Decimal("1")).difference == Decimal("0")


# ── Aislamiento ──────────────────────────────────────────────────────────────


def test_otra_barberia_no_ve_ni_cierra_una_caja_ajena(member, shop, other_shop):
    with tenant_context(shop.pk):
        branch = Branch.objects.create(name="Centro")
        mine = services.open_session(member(Role.CASHIER, shop), branch.public_id, Decimal("0"))
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        with pytest.raises(CashSession.DoesNotExist):
            selectors.session_summary(theirs, mine.public_id)
        with pytest.raises(CashSession.DoesNotExist):
            services.close_session(theirs, mine.public_id, Decimal("0"))
        assert selectors.current_session(theirs, branch.public_id) is None
