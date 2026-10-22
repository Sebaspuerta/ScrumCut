"""Acciones de la pantalla de Comandas (fase F3): cada una es un POST con CSRF que llama a un service.

Las reglas están en `apps.sales.services`; aquí solo se valida el formato y se responde. Un
`ValidationError` se muestra como aviso con su mensaje claro en español. Un objeto de otra sede, de
otro barbero o de otra barbería no se encuentra: 404, sin revelar que existe.
"""

from collections.abc import Callable
from uuid import UUID

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import Form
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.cash.selectors import payment_methods
from apps.core.formatting import format_cop
from apps.sales import services
from apps.sales.board import CLOSED_TODAY
from apps.sales.forms import (
    AddItemForm,
    CancelForm,
    ChangeClientForm,
    CheckoutForm,
    DiscountForm,
    NewOrderForm,
    QuickChargeForm,
)
from apps.tenancy.permissions import require_permission


def _detail(public_id: UUID) -> str:
    return reverse("orders_detail", args=[public_id])


def _form_errors(form: Form) -> str:
    return " ".join(message for errors in form.errors.values() for message in errors)


def _run(request: HttpRequest, action: Callable[[], str], *, back: str) -> HttpResponse:
    """Hace la acción; si sale bien va a donde ella diga, y si no, vuelve con el aviso."""
    try:
        target = action()
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect(back)
    except ObjectDoesNotExist as exc:
        raise Http404 from exc
    return redirect(target)


def _with_form(request: HttpRequest, form: Form, action: Callable[[dict], str], *, back: str) -> HttpResponse:
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return redirect(back)
    return _run(request, lambda: action(form.cleaned_data), back=back)


@require_POST
@require_permission("comandas.crear")
def create(request: HttpRequest) -> HttpResponse:
    """En la sede del alcance; en "todas" `create_order` la rechaza y se pide elegir una sede."""

    def action(data: dict) -> str:
        order = services.create_order(request.membership, request.branch_scope, client=data["cliente"])
        return _detail(order.public_id)

    return _with_form(request, NewOrderForm(request.POST), action, back=reverse("orders_board"))


@require_POST
@require_permission("comandas.editar")
def add_line(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """El precio no viaja en el formulario: `add_item` lo toma del catálogo de la sede."""

    def action(data: dict) -> str:
        services.add_item(
            request.membership,
            public_id,
            scope=request.branch_scope,
            quantity=data["cantidad"],
            barber=data["barbero"],
            **data["item"],
        )
        return _detail(public_id)

    return _with_form(request, AddItemForm(request.POST), action, back=_detail(public_id))


@require_POST
@require_permission("comandas.editar")
def change_client(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """El cliente sale de la barbería activa; uno de otra barbería no se encuentra (lo valida el service)."""

    def action(data: dict) -> str:
        services.change_order_client(request.membership, public_id, scope=request.branch_scope, client=data["cliente"])
        messages.success(request, "Cliente de la comanda actualizado.")
        return _detail(public_id)

    return _with_form(request, ChangeClientForm(request.POST), action, back=_detail(public_id))


@require_POST
@require_permission("comandas.editar")
def remove_line(request: HttpRequest, public_id: UUID, item: UUID) -> HttpResponse:
    def action() -> str:
        services.remove_item(request.membership, public_id, scope=request.branch_scope, item=item)
        return _detail(public_id)

    return _run(request, action, back=_detail(public_id))


@require_POST
@require_permission("comandas.descontar")
def discount(request: HttpRequest, public_id: UUID) -> HttpResponse:
    def action(data: dict) -> str:
        services.set_discount(
            request.membership, public_id, scope=request.branch_scope, amount=data["monto"], reason=data["motivo"]
        )
        return _detail(public_id)

    return _with_form(request, DiscountForm(request.POST), action, back=_detail(public_id))


def _checkout_notice(order, change) -> str:
    """Lo cobrado y, si quedó saldo, lo que quedó como fiado; las vueltas, si hubo efectivo."""
    paid, credit = order.amount_paid, order.total - order.amount_paid
    if not paid and credit:
        return f"Comanda #{order.number} quedó como fiado por {format_cop(credit)}."
    notice = f"Comanda #{order.number} cobrada: {format_cop(paid)}."
    if credit:
        notice += f" Quedó como fiado: {format_cop(credit)}."
    return f"{notice} Vueltas: {format_cop(change)}." if change else notice


@require_POST
@require_permission("comandas.cerrar")
def checkout(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """Un segundo envío del mismo cobro encuentra la comanda cerrada y no cobra dos veces."""
    form = CheckoutForm(request.POST, methods=payment_methods())

    def action(_data: dict) -> str:
        order, change = services.checkout_order(
            request.membership, public_id, scope=request.branch_scope, checkout=form.checkout()
        )
        messages.success(request, _checkout_notice(order, change))
        return f"{reverse('orders_board')}?pestana={CLOSED_TODAY}"

    return _with_form(request, form, action, back=_detail(public_id))


@require_POST
@require_permission("comandas.ver")
def cancel(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """`cancel_order` exige comandas.editar si está abierta y comandas.anular si ya se cerró; queda en la auditoría."""

    def action(data: dict) -> str:
        order = services.cancel_order(request.membership, public_id, scope=request.branch_scope, reason=data["motivo"])
        messages.success(request, f"Comanda #{order.number} anulada.")
        return reverse("orders_board")

    return _with_form(request, CancelForm(request.POST), action, back=_detail(public_id))


@require_POST
@require_permission("comandas.cerrar")
def quick(request: HttpRequest) -> HttpResponse:
    def action(data: dict) -> str:
        order = services.quick_register(
            request.membership,
            request.branch_scope,
            barber=data["barbero"],
            method=data["metodo"],
            reference=data["referencia"],
            **data["item"],
        )
        messages.success(request, f"Comanda #{order.number} cobrada: {format_cop(order.total)}.")
        return f"{reverse('orders_board')}?pestana={CLOSED_TODAY}"

    form = QuickChargeForm(request.POST, methods=payment_methods())
    return _with_form(request, form, action, back=reverse("orders_quick"))
