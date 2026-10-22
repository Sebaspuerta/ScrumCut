"""Formularios de la pantalla de Caja (fase F3). Solo validan el formato: las reglas (una caja abierta
por sede, el esperado, la nota obligatoria con diferencia) están en `apps.cash.services`.
"""

from decimal import Decimal

from django import forms

from apps.cash.models import MovementKind

# Billetes colombianos en circulación, del mayor al menor; las monedas se cuentan como un total en pesos.
BILLS = (100000, 50000, 20000, 10000, 5000, 2000, 1000)
MOVEMENT_FILTERS = (
    ("", "Todos"),
    (MovementKind.SALE, "Ventas"),
    (MovementKind.RECEIVABLE_PAYMENT, "Abonos"),
    (MovementKind.EXPENSE, "Gastos"),
    (MovementKind.WITHDRAWAL, "Retiros"),
)
_MONEY = {"min_value": Decimal("0"), "max_digits": 14, "decimal_places": 2}


def bill_field(bill: int) -> str:
    return f"billetes_{bill}"


class MovementFilterForm(forms.Form):
    tipo = forms.ChoiceField(choices=MOVEMENT_FILTERS, required=False)

    def __init__(self, data) -> None:
        super().__init__(data or {})

    def kind(self) -> str | None:
        return (self.cleaned_data["tipo"] or None) if self.is_valid() else None


class OpenSessionForm(forms.Form):
    base = forms.DecimalField(**_MONEY)


class MovementForm(forms.Form):
    """Gasto o retiro en efectivo; el tipo lo pone la ruta, no el formulario."""

    monto = forms.DecimalField(min_value=Decimal("0.01"), max_digits=14, decimal_places=2)
    concepto = forms.CharField(max_length=200)


class CloseSessionForm(forms.Form):
    """Arqueo por denominación. El contado se suma aquí, en el servidor; el JS solo muestra una vista previa.

    El modelo guarda solo el total contado: el detalle por denominación no se conserva.
    """

    monedas = forms.DecimalField(initial=0, **_MONEY)
    nota = forms.CharField(required=False, max_length=500, widget=forms.Textarea({"rows": 2}))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for bill in BILLS:
            self.fields[bill_field(bill)] = forms.IntegerField(min_value=0, max_value=100000, initial=0)

    def counted(self) -> Decimal:
        bills = sum(Decimal(bill) * self.cleaned_data[bill_field(bill)] for bill in BILLS)
        return bills + self.cleaned_data["monedas"]
