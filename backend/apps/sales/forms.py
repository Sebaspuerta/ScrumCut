"""Formularios de la pantalla de Comandas (fase F3). Solo validan el formato: las reglas de negocio
(precios, saldos, permisos, estados) están en `apps.sales.services`.

Ningún formulario tiene un campo de precio: el precio de una línea sale siempre del catálogo de la
sede (`current_price`), así que un precio enviado desde el navegador no tiene por dónde entrar.
"""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from apps.cash.choices import PaymentMethod
from apps.sales.board import OPEN, TABS, BoardFilter

CASH, TRANSFER, CREDIT = PaymentMethod.CASH, PaymentMethod.TRANSFER, "fiado"
CHECKOUT_METHODS = ((CASH, "Efectivo"), (TRANSFER, "Transferencia"), (CREDIT, "Fiado"))
SERVICE_PREFIX, PRODUCT_PREFIX = "servicio:", "producto:"


class BoardFilterForm(forms.Form):
    """Pestaña, búsqueda y barbero por GET. Un valor inválido vuelve al valor por defecto, sin error."""

    pestana = forms.ChoiceField(choices=TABS, required=False)
    q = forms.CharField(required=False, max_length=60)
    barbero = forms.UUIDField(required=False)

    def __init__(self, data) -> None:
        super().__init__(data or {})

    def filters(self) -> BoardFilter:
        if not self.is_valid():
            return BoardFilter()
        data = self.cleaned_data
        return BoardFilter(tab=data["pestana"] or OPEN, search=data["q"], barber=data["barbero"])


class NewOrderForm(forms.Form):
    cliente = forms.UUIDField(required=False)


class AddItemForm(forms.Form):
    """El ítem viaja como "servicio:<uuid>" o "producto:<uuid>"; el barbero es opcional."""

    item = forms.CharField(max_length=60)
    barbero = forms.UUIDField(required=False)
    cantidad = forms.IntegerField(min_value=1, max_value=99, initial=1)

    def clean_item(self) -> dict:
        value = self.cleaned_data["item"]
        for prefix, kind in ((SERVICE_PREFIX, "service"), (PRODUCT_PREFIX, "product")):
            if value.startswith(prefix):
                return {kind: forms.UUIDField().clean(value.removeprefix(prefix))}
        raise ValidationError("Elige un servicio o un producto.")


class DiscountForm(forms.Form):
    monto = forms.DecimalField(min_value=Decimal("0"), max_digits=14, decimal_places=2)
    motivo = forms.CharField(required=False, max_length=200)


class CheckoutForm(forms.Form):
    """Cobro: efectivo con lo recibido, transferencia con su referencia o fiado con su fecha de pago."""

    metodo = forms.ChoiceField(choices=CHECKOUT_METHODS)
    recibido = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=14, decimal_places=2)
    referencia = forms.CharField(required=False, max_length=80)
    vence = forms.DateField(required=False)

    def clean(self) -> dict:
        cleaned = super().clean()
        if cleaned.get("metodo") == CASH and cleaned.get("recibido") is None:
            raise ValidationError({"recibido": "Indica cuánto recibiste en efectivo."})
        return cleaned


class CancelForm(forms.Form):
    motivo = forms.CharField(max_length=300)
    confirmar = forms.BooleanField(error_messages={"required": "Confirma que quieres anular la comanda."})


class QuickChargeForm(forms.Form):
    """Cobro rápido: un servicio o un producto, cobrado completo (regla 17)."""

    item = AddItemForm.base_fields["item"]
    barbero = forms.UUIDField()
    metodo = forms.ChoiceField(choices=CHECKOUT_METHODS[:2])
    referencia = forms.CharField(required=False, max_length=80)

    clean_item = AddItemForm.clean_item
