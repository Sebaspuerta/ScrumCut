"""Formularios de la pantalla de Fiados (fase F4). Solo validan el formato: que el abono sea mayor que
cero, no pase el saldo y vaya a la sede de origen lo decide `apps.receivables.services.add_payment`.
"""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from apps.receivables.board import OVERDUE, PAID, PENDING, ReceivableFilter

TABS = ((PENDING, "Pendientes"), (OVERDUE, "Vencidos"), (PAID, "Pagados en el mes"))
_MONEY = {"max_digits": 14, "decimal_places": 2}


class ReceivableFilterForm(forms.Form):
    pestana = forms.ChoiceField(choices=TABS, required=False)
    q = forms.CharField(required=False, max_length=60)

    def __init__(self, data) -> None:
        super().__init__(data or {})

    def filters(self) -> ReceivableFilter:
        if not self.is_valid():
            return ReceivableFilter()
        return ReceivableFilter(tab=self.cleaned_data["pestana"] or PENDING, search=self.cleaned_data["q"])


class PaymentForm(forms.Form):
    """El abono. "Pagar todo" envía `pagar_todo`: el monto es entonces el saldo que vio quien abona."""

    monto = forms.DecimalField(required=False, **_MONEY)
    metodo = forms.ChoiceField()
    nota = forms.CharField(required=False, max_length=200)
    saldo_visto = forms.DecimalField(min_value=Decimal("0"), widget=forms.HiddenInput, **_MONEY)
    pagar_todo = forms.BooleanField(required=False)

    def __init__(self, data, *, methods: list[tuple[str, str]]) -> None:
        super().__init__(data)
        self.fields["metodo"].choices = methods

    def clean(self) -> dict:
        cleaned = super().clean()
        if cleaned.get("pagar_todo"):
            cleaned["monto"] = cleaned.get("saldo_visto")
        if cleaned.get("monto") is None:
            raise ValidationError({"monto": "Indica el monto del abono."})
        return cleaned
