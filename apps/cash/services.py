"""Escrituras de caja.

Reglas portadas de MAGNUS v1 (`cash_register_service.py`, `cash_movement_service.py`),
numeradas como en `docs/migracion-magnus.md`: 21–25. Defectos corregidos: 17 (una
caja abierta por sede, garantizada por la base), 18 y 20 (el arqueo sale solo del
libro y se guarda), 19 (métodos de pago cerrados), 21 (un solo libro para todo
dinero). Decisiones 2 y 4.
"""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import record
from apps.cash.models import INCOME_KINDS, OUTFLOW_KINDS, CashMovement, CashSession, Direction, MovementKind
from apps.cash.selectors import expected_cash
from apps.tenancy.models import BarbershopSettings, Branch, Membership
from apps.tenancy.permissions import ensure_permission

_CENTS = Decimal("0.01")

ALREADY_OPEN = "Ya hay una caja abierta en esta sede. Ciérrala antes de abrir otra."
MANUAL_KINDS = (MovementKind.MANUAL_INCOME, MovementKind.EXPENSE, MovementKind.WITHDRAWAL, MovementKind.ADJUSTMENT)


def _audit(actor: Membership, action: str, session: CashSession, *, before: dict | None, after: dict | None) -> None:
    record(
        action=action,
        entity=session._meta.label,
        entity_id=str(session.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        before=before,
        after=after,
    )


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(Decimal(value).quantize(_CENTS))


def _session_snapshot(session: CashSession) -> dict:
    return {
        "branch": str(session.branch.public_id),
        "opening_amount": _money(session.opening_amount),
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        "counted_amount": _money(session.counted_amount),
        "expected_amount": _money(session.expected_amount),
        "difference": _money(session.difference),
    }


def _open_session_in(branch: Branch) -> CashSession | None:
    return CashSession.objects.filter(branch=branch, closed_at__isnull=True).first()


def _locked_open_session(public_id: UUID | str) -> CashSession:
    session = CashSession.objects.select_for_update().get(public_id=public_id)
    if not session.is_open:
        raise ValidationError("La caja está cerrada.")
    return session


def _check_method_enabled(method: str) -> None:
    enabled = BarbershopSettings.objects.get().enabled_payment_methods
    if method not in enabled:
        raise ValidationError({"payment_method": "Ese método de pago no está habilitado en la barbería."})


# ── Libro único ──────────────────────────────────────────────────────────────


def record_money(
    session: CashSession,
    kind: str,
    direction: str,
    method: str,
    amount: Decimal,
    description: str,
    actor: Membership,
) -> CashMovement:
    """Todo dinero, de cualquier método, entra aquí (defecto 21). La usan sales y receivables.

    Bloquea la sesión para que un cierre simultáneo no deje fuera este movimiento.
    No valida permisos: lo hace la operación que la llama.
    """
    with transaction.atomic():
        locked = _locked_open_session(session.public_id)
        _check_method_enabled(method)
        movement = CashMovement(
            barbershop_id=locked.barbershop_id,
            session=locked,
            kind=kind,
            direction=direction,
            payment_method=method,
            amount=amount,
            description=(description or "").strip(),
            created_by=actor.user,
        )
        movement.full_clean()
        movement.save()
    return movement


# ── Sesiones ─────────────────────────────────────────────────────────────────


def open_session(membership: Membership, branch: UUID | str, opening_amount: Decimal, notes: str = "") -> CashSession:
    """Regla 21 por sede (decisión 2). La base garantiza la unicidad aun con solicitudes simultáneas."""
    ensure_permission(membership, "caja.abrir")
    try:
        target = Branch.objects.get(public_id=branch, is_active=True)
    except Branch.DoesNotExist as exc:
        raise ValidationError({"branch": "La sede no existe."}) from exc
    with transaction.atomic():
        if _open_session_in(target) is not None:
            raise ValidationError(ALREADY_OPEN, code="already_open")
        session = CashSession(
            barbershop_id=membership.barbershop_id,
            branch=target,
            opened_by=membership.user,
            opening_amount=opening_amount,
            notes=(notes or "").strip(),
        )
        session.full_clean()
        try:
            with transaction.atomic():
                session.save()
        except IntegrityError as exc:
            raise ValidationError(ALREADY_OPEN, code="already_open") from exc
        _audit(membership, "caja.abrir", session, before=None, after=_session_snapshot(session))
    return session


def close_session(
    membership: Membership, session: UUID | str, counted_amount: Decimal, notes: str | None = None
) -> CashSession:
    """Arqueo (regla 24): esperado = base + entradas en efectivo − salidas en efectivo.

    Sale solo del libro de movimientos y se guarda con el contado y la diferencia.
    """
    ensure_permission(membership, "caja.cerrar")
    with transaction.atomic():
        target = _locked_open_session(session)
        before = _session_snapshot(target)
        # El campo convierte y valida (≥ 0) antes de calcular la diferencia.
        target.counted_amount = CashSession._meta.get_field("counted_amount").clean(counted_amount, target)
        target.expected_amount = expected_cash(target)
        target.difference = target.counted_amount - target.expected_amount
        target.closed_by = membership.user
        target.closed_at = timezone.now()
        if notes:
            target.notes = notes.strip()
        target.full_clean()
        target.save()
        _audit(membership, "caja.cerrar", target, before=before, after=_session_snapshot(target))
    return target


def register_manual_movement(
    membership: Membership,
    session: UUID | str,
    kind: str,
    amount: Decimal,
    payment_method: str,
    description: str,
    direction: str | None = None,
) -> CashMovement:
    """Regla 25: ingreso, gasto, retiro o ajuste en una caja abierta.

    El sentido sale del tipo; solo un ajuste exige indicarlo.
    """
    ensure_permission(membership, "caja.movimiento")
    if kind not in MANUAL_KINDS:
        raise ValidationError({"kind": "Tipo de movimiento manual no válido."})
    if kind in INCOME_KINDS:
        direction = Direction.IN
    elif kind in OUTFLOW_KINDS:
        direction = Direction.OUT
    elif direction not in Direction.values:
        raise ValidationError({"direction": "Indica si el ajuste entra o sale."})
    target = CashSession.objects.get(public_id=session)
    return record_money(target, kind, direction, payment_method, amount, description, membership)
