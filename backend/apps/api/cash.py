"""Caja en la app de React: lo mismo que lee la pantalla de Django (`cash.board.cash_register`), en JSON.

Siempre de una sede: en "todas" no se mezclan cajas. El esperado sale de `expected_cash`, el mismo cálculo
del arqueo; el contado lo suma el servidor al cerrar. Qué acciones permite el rol lo decide el backend.
"""

from django.core.paginator import Page

from apps.accounts.models import User
from apps.cash.board import cash_register
from apps.cash.forms import BILLS, MOVEMENT_FILTERS
from apps.cash.models import CashMovement, CashSession, MovementKind
from apps.sales.selectors import local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import role_has_permission

# Lo que se registra a mano desde la pantalla, siempre en efectivo (la pantalla de Django: gasto y retiro).
MANUAL_KINDS = (MovementKind.MANUAL_INCOME, MovementKind.EXPENSE, MovementKind.WITHDRAWAL)
STRIP_KEYS = {
    MovementKind.SALE: "sales",
    MovementKind.RECEIVABLE_PAYMENT: "receivable_payments",
    MovementKind.EXPENSE: "expenses",
    MovementKind.WITHDRAWAL: "withdrawals",
}


def person(user: User) -> str:
    return user.full_name or user.email


def _movement(movement: CashMovement) -> dict:
    return {
        "id": movement.public_id,
        "at": movement.created_at,
        "kind": movement.kind,
        "kind_label": movement.get_kind_display(),
        "description": movement.description,
        "by": person(movement.created_by),
        "direction": movement.direction,
        "amount": movement.amount,
    }


def _session(data: dict) -> dict:
    session: CashSession = data["session"]
    return {
        "id": session.public_id,
        "opened_at": session.opened_at,
        "opened_by": person(session.opened_by),
        "stale": data["stale"],
        "opening_amount": session.opening_amount,
        "strip": {key: data["by_kind"][kind] for kind, key in STRIP_KEYS.items()},
        "expected": data["expected"],
        "movements": [_movement(movement) for movement in data["movements"]],
        "other_media": data["other_media"],
    }


def _actions(membership: Membership, data: dict) -> dict[str, bool]:
    """Abrir sin caja; registrar solo en una caja de hoy (la de otro día solo se cierra); cerrar con caja."""
    session, role = data.get("session"), membership.role
    return {
        "open": not data["needs_branch"] and session is None and role_has_permission(role, "caja.abrir"),
        "movement": session is not None and not data["stale"] and role_has_permission(role, "caja.movimiento"),
        "close": session is not None and role_has_permission(role, "caja.cerrar"),
    }


def cash_state(membership: Membership, *, scope: BranchScope, kind: str | None) -> dict:
    data = cash_register(membership, scope=scope, kind=kind)
    data.setdefault("stale", False)
    return {
        "needs_branch": data["needs_branch"],
        "branch": scope.branch.name if scope.branch else None,
        "today": local_today(membership),
        "kind": kind or "",
        "kinds": [{"value": value, "label": label} for value, label in MOVEMENT_FILTERS],
        "manual_kinds": [{"value": value.value, "label": value.label} for value in MANUAL_KINDS],
        "denominations": list(BILLS),
        "session": _session(data) if data.get("session") else None,
        "actions": _actions(membership, data),
    }


def closing_row(session: CashSession) -> dict:
    return {
        "id": session.public_id,
        "branch": session.branch.name,
        "closed_at": session.closed_at,
        "closed_by": person(session.closed_by),
        "expected": session.expected_amount,
        "counted": session.counted_amount,
        "difference": session.difference,
        "notes": session.notes,
    }


def closings(page: Page) -> dict:
    return {
        "count": page.paginator.count,
        "page": page.number,
        "pages": page.paginator.num_pages,
        "page_size": page.paginator.per_page,
        "results": [closing_row(session) for session in page],
    }
