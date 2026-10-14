"""Filtros del tablero y de la exportación, validados en el servidor."""

from datetime import date

from django import forms
from django.core.exceptions import ValidationError

MAX_RANGE_DAYS = 366


class PeriodFilterForm(forms.Form):
    """Período por GET: ?periodo=30d|mes|rango&desde=&hasta=&sede=. Sin datos válidos: los últimos 30 días."""

    periodo = forms.ChoiceField(
        label="Período",
        required=False,
        choices=[("30d", "Últimos 30 días"), ("mes", "Este mes"), ("rango", "Rango personalizado")],
    )
    desde = forms.DateField(label="Desde", required=False, widget=forms.DateInput({"type": "date"}, "%Y-%m-%d"))
    hasta = forms.DateField(label="Hasta", required=False, widget=forms.DateInput({"type": "date"}, "%Y-%m-%d"))
    sede = forms.ChoiceField(label="Sede", required=False)

    def __init__(self, data, *, branches, today: date) -> None:
        super().__init__(data or {})  # siempre ligado: sin filtros, todo vacío y válido
        self.branches = list(branches)
        self.today = today
        self.fields["sede"].choices = [(str(branch.public_id), branch.name) for branch in self.branches]

    def clean(self) -> dict:
        cleaned = super().clean()
        if cleaned.get("periodo") != "rango":
            return cleaned
        start, end = cleaned.get("desde"), cleaned.get("hasta")
        if not start or not end:
            raise ValidationError("Indica las dos fechas del rango.")
        if start > end:
            raise ValidationError("La fecha inicial no puede ser posterior a la final.")
        if (end - start).days + 1 > MAX_RANGE_DAYS:
            raise ValidationError(f"El rango no puede pasar de {MAX_RANGE_DAYS} días.")
        return cleaned

    def dates(self) -> tuple[date | None, date | None]:
        """(None, None) son los últimos 30 días contando hoy, el período por defecto."""
        if not self.is_valid():
            return None, None
        chosen = self.cleaned_data.get("periodo")
        if chosen == "mes":
            return self.today.replace(day=1), self.today
        if chosen == "rango":
            return self.cleaned_data["desde"], self.cleaned_data["hasta"]
        return None, None

    def branch(self):
        """La sede elegida (aunque el rango no sea válido) o, si no hay una válida, la primera."""
        self.is_valid()
        chosen = self.cleaned_data.get("sede")
        default = self.branches[0] if self.branches else None
        return next((branch for branch in self.branches if str(branch.public_id) == chosen), default)
