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
from apps.sales.services.checkout import MAX_PARTS, Checkout, PaymentPart

CASH, CREDIT = PaymentMethod.CASH, "fiado"
_MONEY = {"max_digits": 14, "decimal_places": 2}
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


class ChangeClientForm(forms.Form):
    """El cliente elegido; vacío deja la comanda como de mostrador."""

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


def _part_fields(number: int) -> dict[str, forms.Field]:
    return {
        f"parte_{number}_metodo": forms.ChoiceField(required=False),
        f"parte_{number}_monto": forms.DecimalField(required=False, min_value=Decimal("0.01"), **_MONEY),
        f"parte_{number}_referencia": forms.CharField(required=False, max_length=80),
    }


class CheckoutForm(forms.Form):
    """Cobro con una forma de pago o dividido en hasta tres partes ("parte_1_metodo", "parte_1_monto"...).

    Sin JavaScript se elige una sola forma; el JS solo muestra las filas para dividir. Que las partes sumen
    el total y las vueltas los decide `checkout_order`.
    """

    metodo = forms.ChoiceField()
    recibido = forms.DecimalField(required=False, min_value=Decimal("0"), **_MONEY)
    referencia = forms.CharField(required=False, max_length=80)
    vence = forms.DateField(required=False)

    def __init__(self, data, *, methods: list[tuple[str, str]]) -> None:
        super().__init__(data)
        for number in range(1, MAX_PARTS + 1):
            self.fields.update(_part_fields(number))
        choices = [*methods, (CREDIT, "Fiado")]
        for name, field in self.fields.items():
            if name == "metodo" or name.endswith("_metodo"):
                field.choices = choices if name == "metodo" else [("", "—"), *choices]

    def _parts(self) -> list[PaymentPart]:
        data = self.cleaned_data
        rows = [n for n in range(1, MAX_PARTS + 1) if data.get(f"parte_{n}_monto") is not None]
        if not rows:
            return [PaymentPart(data["metodo"], reference=data.get("referencia", ""))]
        if any(not data.get(f"parte_{n}_metodo") for n in rows):
            raise ValidationError("Elige la forma de pago de cada parte.")
        return [
            PaymentPart(data[f"parte_{n}_metodo"], data[f"parte_{n}_monto"], data[f"parte_{n}_referencia"])
            for n in rows
        ]

    def clean(self) -> dict:
        cleaned = super().clean()
        if self.errors:
            return cleaned
        cleaned["parts"] = tuple(self._parts())
        if any(part.method == CASH for part in cleaned["parts"]) and cleaned.get("recibido") is None:
            raise ValidationError({"recibido": "Indica cuánto recibiste en efectivo."})
        return cleaned

    def checkout(self) -> Checkout:
        data = self.cleaned_data
        return Checkout(parts=data["parts"], received=data["recibido"], due_date=data["vence"])


class CancelForm(forms.Form):
    motivo = forms.CharField(max_length=300)
    confirmar = forms.BooleanField(error_messages={"required": "Confirma que quieres anular la comanda."})


class QuickChargeForm(forms.Form):
    """Cobro rápido: un servicio o un producto, cobrado completo (regla 17)."""

    item = AddItemForm.base_fields["item"]
    barbero = forms.UUIDField()
    metodo = forms.ChoiceField()
    referencia = forms.CharField(required=False, max_length=80)

    def __init__(self, data, *, methods: list[tuple[str, str]]) -> None:
        super().__init__(data)
        self.fields["metodo"].choices = methods

    clean_item = AddItemForm.clean_item
