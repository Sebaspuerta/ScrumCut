"""Pantalla de Caja (fase F3): apertura, franja del día, gastos y retiros, movimientos y arqueo con cierre.

Siempre de una sede: en "todas" se pide elegir una. Las vistas solo validan el formato y llaman a los
services de `apps.cash`; la caja de otra sede no se encuentra (404), igual que la de otra barbería.
"""

from collections.abc import Callable
from uuid import UUID

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import Form
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.cash import services
from apps.cash.board import cash_register
from apps.cash.choices import PaymentMethod
from apps.cash.forms import (
    BILLS,
    MOVEMENT_FILTERS,
    CloseSessionForm,
    MovementFilterForm,
    MovementForm,
    OpenSessionForm,
    bill_field,
)
from apps.cash.models import MovementKind
from apps.core.formatting import format_cop, format_difference
from apps.tenancy.permissions import require_permission
from apps.tenancy.roles import role_has_permission

TEMPLATE = "cash/register.html"
MANUAL = {"gasto": MovementKind.EXPENSE, "retiro": MovementKind.WITHDRAWAL}
MANUAL_TITLES = (("gasto", "Registrar gasto"), ("retiro", "Registrar retiro"))
PERMISSIONS = {"open": "caja.abrir", "movement": "caja.movimiento", "close": "caja.cerrar"}


def _back() -> str:
    return reverse("cash_register")


def _run(request: HttpRequest, form: Form, action: Callable[[dict], str]) -> HttpResponse:
    """Valida el formato, hace la acción y vuelve a la caja con su aviso."""
    if not form.is_valid():
        messages.error(request, " ".join(m for errors in form.errors.values() for m in errors))
        return redirect(_back())
    try:
        messages.success(request, action(form.cleaned_data))
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    return redirect(_back())


@require_GET
@require_permission("caja.ver")
def register(request: HttpRequest) -> HttpResponse:
    kind = MovementFilterForm(request.GET).kind()
    data = cash_register(request.membership, scope=request.branch_scope, kind=kind)
    can = {name: role_has_permission(request.membership.role, code) for name, code in PERMISSIONS.items()}
    bills = [{"value": bill, "field": bill_field(bill)} for bill in BILLS]
    extra = {"can": can, "kind": kind or "", "kinds": MOVEMENT_FILTERS, "bills": bills, "manual_kinds": MANUAL_TITLES}
    return render(request, TEMPLATE, {**data, **extra})


@require_POST
@require_permission("caja.abrir")
def open_session(request: HttpRequest) -> HttpResponse:
    def action(data: dict) -> str:
        services.open_session(request.membership, request.branch_scope, opening_amount=data["base"])
        return f"Caja abierta con una base de {format_cop(data['base'])}."

    return _run(request, OpenSessionForm(request.POST), action)


@require_POST
@require_permission("caja.movimiento")
def manual_movement(request: HttpRequest, session: UUID, kind: str) -> HttpResponse:
    """Gasto o retiro en efectivo de la caja abierta; después de cerrar, `record_money` lo rechaza."""
    if kind not in MANUAL:
        raise Http404

    def action(data: dict) -> str:
        services.register_manual_movement(
            request.membership,
            session,
            scope=request.branch_scope,
            kind=MANUAL[kind],
            amount=data["monto"],
            payment_method=PaymentMethod.CASH,
            description=data["concepto"],
        )
        return f"{kind.capitalize()} de {format_cop(data['monto'])} registrado."

    return _run(request, MovementForm(request.POST), action)


@require_POST
@require_permission("caja.cerrar")
def close_session(request: HttpRequest, session: UUID) -> HttpResponse:
    """El contado se suma en el servidor; con diferencia, `close_session` exige la nota."""
    form = CloseSessionForm(request.POST)

    def action(data: dict) -> str:
        closed = services.close_session(
            request.membership, session, scope=request.branch_scope, counted_amount=form.counted(), notes=data["nota"]
        )
        return (
            f"Caja cerrada con {format_cop(closed.counted_amount)}. Diferencia: {format_difference(closed.difference)}."
        )

    return _run(request, form, action)
