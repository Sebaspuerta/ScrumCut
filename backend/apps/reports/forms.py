"""Filtro del tablero y de la exportación, validado en el servidor: el mes (?mes=AAAA-MM) y la vista de las
ventas (?vista=tabla|3d) por GET. Nada se guarda en el navegador: lo que se ve va en la URL."""

from datetime import date

from django import forms

from apps.core.formatting import month_label

MONTH_FORMAT = "%Y-%m"
TABLE_VIEW, TOWERS_VIEW = "tabla", "3d"


def _months_between(first: date, last: date) -> list[date]:
    """Del mes de `last` hacia atrás hasta el de `first`, como primer día de cada mes."""
    months, current = [], last.replace(day=1)
    while current >= first.replace(day=1):
        months.append(current)
        current = date(current.year - (current.month == 1), (current.month - 2) % 12 + 1, 1)
    return months


class MonthFilterForm(forms.Form):
    """Sin valor, con un formato inválido, en el futuro o antes de que existiera la barbería: el mes actual.

    Nunca da error: un enlace viejo o editado a mano solo vuelve al mes actual. La sede no viaja en
    la URL: es el alcance de la sesión (request.branch_scope, docs/sedes.md).
    """

    mes = forms.CharField(required=False, max_length=7)
    vista = forms.CharField(required=False, max_length=8)

    def __init__(self, data, *, today: date, since: date) -> None:
        super().__init__(data or {})  # siempre ligado: sin filtro, vacío y válido
        self.today, self.since = today, since

    def month(self) -> date:
        current = self.today.replace(day=1)
        if not self.is_valid():
            return current
        try:
            chosen = date.fromisoformat(f"{self.cleaned_data['mes']}-01")
        except ValueError:
            return current
        return chosen if self.since.replace(day=1) <= chosen <= current else current

    def view(self) -> str:
        """La vista de las ventas por día: "3d" solo si se pidió así; cualquier otro valor, la tabla."""
        return TOWERS_VIEW if self.is_valid() and self.cleaned_data["vista"] == TOWERS_VIEW else TABLE_VIEW

    def choices(self) -> list[dict]:
        """Los meses que se pueden elegir, del actual al de la creación de la barbería."""
        chosen = self.month()
        return [
            {
                "value": month.strftime(MONTH_FORMAT),
                "label": month_label(month),
                "selected": month == chosen,
            }
            for month in _months_between(self.since, self.today)
        ]
