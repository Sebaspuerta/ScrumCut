"""Escrituras de fiados.

Reglas portadas de MAGNUS v1 (`accounts_receivable_service.py`), numeradas como
en `docs/migracion-magnus.md`: 26–28. Defectos corregidos: 24 (abonos con bloqueo,
sin pasar del saldo ni a fiados cerrados) y 25 (marcar vencidos es una tarea, no
un efecto de leer).
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import record
from apps.cash.models import Direction, MovementKind
from apps.cash.selectors import open_session_for
from apps.cash.services import record_money
from apps.clients.models import Client
from apps.receivables.models import OPEN_STATUSES, Receivable, ReceivablePayment, ReceivableStatus
from apps.receivables.selectors import client_balance
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import BarbershopSettings, Branch, Membership
from apps.tenancy.permissions import ensure_permission

_CENTS = Decimal("0.01")
OTHER_BRANCH_PAYMENT = "Este fiado se abona en su sede de origen."


def _audit(actor: Membership, action: str, *, receivable: Receivable, before: dict | None, after: dict) -> None:
    """La sede del evento es la de origen del fiado: ahí nace, se abona y se anula (decisión 3)."""
    record(
        action=action,
        entity=receivable._meta.label,
        entity_id=str(receivable.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        branch=receivable.origin_branch,
        before=before,
        after=after,
    )


def _snapshot(receivable: Receivable) -> dict:
    return {
        "client": str(receivable.client.public_id),
        "order": str(receivable.order.public_id) if receivable.order_id else None,
        "origin_branch": str(receivable.origin_branch.public_id),
        "total": str(Decimal(receivable.total).quantize(_CENTS)),
        "balance": str(Decimal(receivable.balance).quantize(_CENTS)),
        "status": receivable.status,
        "due_date": receivable.due_date.isoformat() if receivable.due_date else None,
    }


def _check_credit_limit(client: Client, amount: Decimal, *, branch: Branch) -> None:
    """Bloquea al cliente para que dos fiados simultáneos no pasen juntos el límite.

    Cuenta la deuda de la sede: los fiados son de cada sede (decisión 15), y el mensaje
    no debe revelar lo que el cliente debe en otra.
    """
    Client.objects.select_for_update().get(pk=client.pk)
    limit = BarbershopSettings.objects.get().max_credit_per_client
    if limit is None:
        return
    debt = client_balance(client, branch=branch)
    if debt + amount > limit:
        raise ValidationError(
            "El cliente superaría su límite de crédito: debe %(debt)s y el límite es %(limit)s.",
            code="credit_limit",
            params={"debt": debt, "limit": limit},
        )


def _create(
    client: Client,
    total: Decimal,
    *,
    actor: Membership,
    origin_branch: Branch,
    order=None,
    due_date=None,
    notes="",
) -> Receivable:
    _check_credit_limit(client, total, branch=origin_branch)
    receivable = Receivable(
        barbershop_id=client.barbershop_id,
        client=client,
        order=order,
        origin_branch=origin_branch,
        total=total,
        balance=total,
        due_date=due_date,
        notes=(notes or "").strip(),
        created_by=actor.user,
    )
    receivable.full_clean()
    receivable.save()
    _audit(actor, "fiado.crear", receivable=receivable, before=None, after=_snapshot(receivable))
    return receivable


def create_from_order(order, amount: Decimal, *, actor: Membership, due_date: date | None = None) -> Receivable:
    """Saldo de una comanda cerrada como fiado, con la sede de la comanda. La usa sales, que ya validó."""
    return _create(order.client, amount, actor=actor, origin_branch=order.branch, order=order, due_date=due_date)


def create_manual(
    membership: Membership,
    client: UUID | str,
    *,
    scope: BranchScope,
    total: Decimal,
    due_date: date | None = None,
    notes: str = "",
) -> Receivable:
    """Regla 26: fiado sin comanda, a un cliente vivo y no anonimizado, con total > 0.

    Nace en la sede del alcance, que queda como su sede de origen (decisión 3); en "todas", no.
    """
    ensure_permission(membership, "fiados.crear")
    try:
        target = Client.objects.get(public_id=client, deleted_at__isnull=True, anonymized_at__isnull=True)
    except Client.DoesNotExist as exc:
        raise ValidationError({"client": "El cliente no existe."}) from exc
    origin = scope.branch_for_write(membership)
    with transaction.atomic():
        return _create(target, total, actor=membership, origin_branch=origin, due_date=due_date, notes=notes)


def _locked_open_receivable(public_id: UUID | str, amount: Decimal) -> Receivable:
    locked = Receivable.objects.select_for_update().get(public_id=public_id)
    if locked.status not in OPEN_STATUSES:
        raise ValidationError("Este fiado ya está pagado o anulado.")
    if amount > locked.balance:
        raise ValidationError(
            "El abono supera el saldo de %(balance)s.", code="over_balance", params={"balance": locked.balance}
        )
    return locked


def _record_payment(
    locked: Receivable, session, *, membership: Membership, amount: Decimal, method: str
) -> ReceivablePayment:
    """El dinero entra a la caja de la sesión, que es de la sede de origen del fiado (no se guarda aparte)."""
    movement = record_money(
        session,
        MovementKind.RECEIVABLE_PAYMENT,
        direction=Direction.IN,
        method=method,
        amount=amount,
        description=f"Abono a fiado de {locked.client}",
        actor=membership,
    )
    payment = ReceivablePayment(
        barbershop_id=locked.barbershop_id,
        receivable=locked,
        cash_movement=movement,
        amount=amount,
        method=method,
        received_by=membership.user,
    )
    payment.full_clean()
    payment.save()
    locked.balance -= amount
    if locked.balance == 0:
        locked.status = ReceivableStatus.PAID
    locked.full_clean()
    locked.save(update_fields=["balance", "status", "updated_at"])
    return payment


def add_payment(
    membership: Membership, receivable: UUID | str, *, scope: BranchScope, amount: Decimal, method: str
) -> ReceivablePayment:
    """Regla 27 con el defecto 24 corregido: monto ≤ saldo, solo a fiados vivos, con caja abierta.

    Decisión 3 de docs/sedes.md: el abono entra solo a la caja de la sede de origen del fiado, que
    debe ser la del alcance y estar activa; ninguna operación de dinero cruza sedes. Cualquier método,
    un solo libro.
    """
    ensure_permission(membership, "fiados.abonar")
    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError({"amount": "El abono debe ser mayor que cero."})
    target_branch = scope.branch_for_write(membership)
    with transaction.atomic():
        locked = _locked_open_receivable(receivable, amount)
        if locked.origin_branch_id != target_branch.pk:
            raise ValidationError({"branch": OTHER_BRANCH_PAYMENT})
        session = open_session_for(target_branch)
        if session is None:
            raise ValidationError("No hay una caja abierta en esta sede para recibir el abono.", code="no_open_session")
        before = _snapshot(locked)
        payment = _record_payment(locked, session, membership=membership, amount=amount, method=method)
        _audit(membership, "fiado.abonar", receivable=locked, before=before, after=_snapshot(locked))
    return payment


def _cancel(locked: Receivable, actor: Membership, *, reason: str) -> Receivable:
    if locked.payments.exists():
        raise ValidationError(
            "El fiado ya tiene abonos: primero hay que devolverlos o resolverlos antes de anularlo.",
            code="has_payments",
        )
    if locked.status not in OPEN_STATUSES:
        raise ValidationError("Este fiado ya está anulado.")
    before = _snapshot(locked)
    locked.status = ReceivableStatus.CANCELLED
    locked.balance = Decimal("0")
    locked.save(update_fields=["status", "balance", "updated_at"])
    _audit(actor, "fiado.anular", receivable=locked, before=before, after={**_snapshot(locked), "reason": reason})
    return locked


def cancel_receivable(membership: Membership, receivable: UUID | str, *, reason: str) -> Receivable:
    """Solo sin abonos. Exige motivo."""
    ensure_permission(membership, "fiados.anular")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "El motivo es obligatorio."})
    with transaction.atomic():
        return _cancel(Receivable.objects.select_for_update().get(public_id=receivable), membership, reason=reason)


def cancel_for_order(order, actor: Membership, *, reason: str) -> Receivable | None:
    """Anula el fiado de una comanda que se está anulando. La usa sales con `comandas.anular`."""
    locked = Receivable.objects.select_for_update().filter(order=order).first()
    if locked is None or locked.status == ReceivableStatus.CANCELLED:
        return None
    return _cancel(locked, actor, reason=reason)


def mark_overdue(today: date) -> int:
    """Regla 28 para la tarea programada: pendientes con saldo y vencimiento anterior a `today`.

    Opera en la barbería activa (tenant_context); nunca se llama al leer.
    """
    return Receivable.objects.filter(
        status=ReceivableStatus.PENDING, balance__gt=0, due_date__isnull=False, due_date__lt=today
    ).update(status=ReceivableStatus.OVERDUE)
