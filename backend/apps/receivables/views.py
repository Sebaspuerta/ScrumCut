"""Pantalla de Fiados (fase F4): cartera de la sede, antigüedad, lista por urgencia y abono.

Las vistas solo reciben, validan el formato y responden. El abono usa `add_payment`: va a la caja de la
sede de origen del fiado, respeta la regla de la caja de otro día y queda en la auditoría. En "todas"
se ve la cartera consolidada, pero para abonar hay que elegir la sede del fiado.
"""

from uuid import UUID

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.cash.selectors import payment_methods
from apps.core.formatting import format_cop
from apps.receivables import services
from apps.receivables.board import (
    aging,
    collected_this_month,
    due_status,
    portfolio,
    receivable_detail,
    receivable_rows,
)
from apps.receivables.forms import TABS, PaymentForm, ReceivableFilterForm
from apps.receivables.models import Receivable
from apps.sales.selectors import day_bounds, local_today
from apps.tenancy.permissions import require_permission
from apps.tenancy.roles import role_has_permission

TEMPLATE = "receivables/board.html"


def _row(receivable: Receivable, today) -> dict:
    return {
        "receivable": receivable,
        "status": due_status(receivable, today),
        "paid": receivable.total - receivable.balance,
    }


def _board(request: HttpRequest) -> dict:
    membership, scope = request.membership, request.branch_scope
    today = local_today(membership)
    month_start = day_bounds(membership.barbershop.timezone, today.replace(day=1), today)[0]
    filters = ReceivableFilterForm(request.GET).filters()
    data = portfolio(membership, scope=scope, today=today, month_start=month_start)
    rows = receivable_rows(membership, scope=scope, filters=filters, today=today, month_start=month_start)
    return {
        "filters": filters,
        "data": data,
        "aging": aging(data),
        "collected": collected_this_month(membership, scope=scope, month_start=month_start),
        "tabs": [{"value": value, "label": label, "count": data[f"{value}_count"]} for value, label in TABS],
        "rows": [_row(receivable, today) for receivable in rows],
        "today": today,
        "can_pay": role_has_permission(membership.role, "fiados.abonar"),
    }


@require_GET
@require_permission("fiados.ver")
def board(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE, _board(request))


@require_GET
@require_permission("fiados.ver")
def detail(request: HttpRequest, public_id: UUID) -> HttpResponse:
    try:
        selected = receivable_detail(request.membership, public_id, scope=request.branch_scope)
    except Receivable.DoesNotExist as exc:
        raise Http404 from exc
    context = _board(request)
    context["selected"] = _row(selected, context["today"])
    context["methods"] = payment_methods()
    return render(request, TEMPLATE, context)


def _notice(payment) -> str:
    receivable = payment.receivable
    if receivable.balance == 0:
        return f"Abono de {format_cop(payment.amount)} registrado: el fiado quedó pagado."
    return f"Abono de {format_cop(payment.amount)} registrado. Saldo: {format_cop(receivable.balance)}."


@require_POST
@require_permission("fiados.abonar")
def pay(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """Un doble envío se rechaza: el segundo ya no ve el saldo que vio el primero (`expected_balance`)."""
    back = reverse("receivables_detail", args=[public_id])
    form = PaymentForm(request.POST, methods=payment_methods())
    if not form.is_valid():
        messages.error(request, " ".join(m for errors in form.errors.values() for m in errors))
        return redirect(back)
    data = form.cleaned_data
    try:
        payment = services.add_payment(
            request.membership,
            public_id,
            scope=request.branch_scope,
            amount=data["monto"],
            method=data["metodo"],
            note=data["nota"],
            expected_balance=data["saldo_visto"],
        )
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect(back)
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    messages.success(request, _notice(payment))
    return redirect(back)
