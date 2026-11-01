"""Fiados en la app de React: lo mismo que lee la pantalla de Django (`receivables.board`), en JSON.

Por la sede de origen de cada fiado (decisión 3 de docs/sedes.md). La cartera, la antigüedad, el estado en texto
y qué acciones permite el rol los decide el backend; el abono lo valida `receivables.services.add_payment`.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from apps.api.cash import person
from apps.cash.selectors import payment_methods
from apps.receivables.board import (
    OVERDUE,
    PENDING,
    ReceivableFilter,
    aging,
    collected_this_month,
    due_status,
    portfolio,
    receivable_detail,
    receivable_rows,
)
from apps.receivables.forms import TABS
from apps.receivables.models import OPEN_STATUSES, Receivable
from apps.sales.selectors import local_today, month_start
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import role_has_permission

PERCENT = 100


def receivable_row(receivable: Receivable, today: date) -> dict:
    """Un fiado de la lista: cliente, comanda, fechas, total, abonado, saldo y el estado en texto, sin rojos."""
    status = due_status(receivable, today)
    order = receivable.order
    return {
        "id": receivable.public_id,
        "client": {"id": receivable.client.public_id, "name": receivable.client.full_name},
        "order": {"id": order.public_id, "number": order.number} if order else None,
        "branch": receivable.origin_branch.name,
        "created_at": receivable.created_at,
        "due_date": receivable.due_date,
        "total": receivable.total,
        "paid": receivable.total - receivable.balance,
        "balance": receivable.balance,
        "status": receivable.status,
        "due_text": status["text"],
        "due_tone": status["tone"],
    }


def _share(part: Decimal, total: Decimal) -> int | None:
    return round(part * PERCENT / total) if total else None


def _portfolio(data: dict, collected: dict) -> dict:
    """La franja: por cobrar, vencido (con su parte de la cartera), vence en 7 días y cobrado en el mes."""
    pending = data[f"{PENDING}_total"]
    return {
        "pending": {"total": pending, "count": data[f"{PENDING}_count"], "clients": data[f"{PENDING}_clients"]},
        "overdue": {
            "total": data[f"{OVERDUE}_total"],
            "clients": data[f"{OVERDUE}_clients"],
            "share": _share(data[f"{OVERDUE}_total"], pending),
        },
        "due_soon": {"total": data["due_soon_total"], "clients": data["due_soon_clients"]},
        "collected": collected,
    }


def receivable_list(membership: Membership, *, scope: BranchScope, filters: ReceivableFilter, page: int) -> dict:
    """La cartera de las sedes del alcance, la antigüedad, el conteo de cada pestaña y una página de la elegida."""
    today, start = local_today(membership), month_start(membership)
    data = portfolio(membership, scope=scope, today=today, month_start=start)
    rows = receivable_rows(membership, scope=scope, filters=filters, today=today, month_start=start, page=page)
    collected = collected_this_month(membership, scope=scope, month_start=start)
    return {
        "today": today,
        "tab": filters.tab,
        "tabs": [{"value": value, "label": label, "count": data[f"{value}_count"]} for value, label in TABS],
        "portfolio": _portfolio(data, collected),
        "aging": aging(data),
        "count": rows.paginator.count,
        "page": rows.number,
        "pages": rows.paginator.num_pages,
        "page_size": rows.paginator.per_page,
        "results": [receivable_row(receivable, today) for receivable in rows],
    }


def _can_pay(membership: Membership, receivable: Receivable) -> bool:
    alive = receivable.status in OPEN_STATUSES and receivable.balance > 0
    return alive and role_has_permission(membership.role, "fiados.abonar")


def receivable_data(membership: Membership, public_id: UUID | str, *, scope: BranchScope) -> dict:
    """El fiado con sus abonos. En "todas" se lee, pero para abonar hay que elegir su sede de origen."""
    receivable = receivable_detail(membership, public_id, scope=scope)
    can_pay = _can_pay(membership, receivable)
    return {
        **receivable_row(receivable, local_today(membership)),
        "notes": receivable.notes,
        "payments": [
            {
                "id": payment.public_id,
                "at": payment.created_at,
                "method": payment.get_method_display(),
                "reference": payment.reference,
                "amount": payment.amount,
                "received_by": person(payment.received_by),
            }
            for payment in receivable.payments.all()
        ],
        "methods": [{"value": value, "label": label} for value, label in payment_methods()],
        "actions": {"pay": can_pay and scope.branch is not None},
        "needs_branch": can_pay and scope.branch is None,
    }
