"""Formularios de la pantalla de Clientes (fase F4). Solo validan el formato: los duplicados, la
autorización de datos y la auditoría están en `apps.clients.services`.
"""

import re

from django import forms
from django.core.exceptions import ValidationError

from apps.clients.board import ORDERINGS, ClientFilter
from apps.clients.selectors import ClientStatus

MOBILE = re.compile(r"(57)?3\d{9}")
INVALID_MOBILE = "Escribe un celular colombiano de 10 dígitos que empiece por 3 (por ejemplo, 300 123 4567)."
LEVELS = [("", "Todos"), *ClientStatus.choices]
ORDER_LABELS = (
    ("ultima", "Última visita"),
    ("visitas", "Más visitas"),
    ("gasto", "Mayor gasto"),
    ("deuda", "Mayor deuda"),
)
HIDDEN_ON_EDIT = ("phone", "document")


def level_chips(counts: dict, selected: str) -> list[dict]:
    """Los filtros por nivel con su conteo; "Todos" suma también a los encontrados sin visitas en la sede."""
    total = sum(counts.values())
    return [
        {"value": value, "label": label, "count": counts.get(value, 0) if value else total, "on": value == selected}
        for value, label in LEVELS
    ]


class ClientFilterForm(forms.Form):
    """Búsqueda, nivel y orden por GET. Un valor inválido vuelve al valor por defecto, sin error."""

    q = forms.CharField(required=False, max_length=60)
    nivel = forms.ChoiceField(choices=LEVELS, required=False)
    orden = forms.ChoiceField(choices=[(key, key) for key in ORDERINGS], required=False)

    def __init__(self, data) -> None:
        super().__init__(data or {})

    def filters(self) -> ClientFilter:
        if not self.is_valid():
            return ClientFilter()
        data = self.cleaned_data
        return ClientFilter(search=data["q"], level=data["nivel"], order=data["orden"] or "ultima")


class ClientForm(forms.Form):
    """Datos de la persona (de la barbería). El celular, si se escribe, debe ser colombiano."""

    full_name = forms.CharField(label="Nombre completo", max_length=120)
    phone = forms.CharField(label="Celular", max_length=20, required=False)
    document = forms.CharField(label="Cédula", max_length=20, required=False)
    email = forms.EmailField(label="Correo", required=False)
    notes = forms.CharField(
        label="Preferencias y notas", required=False, max_length=1000, widget=forms.Textarea({"rows": 3})
    )
    other_person = forms.BooleanField(label="Es otra persona con el mismo nombre", required=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field, forms.BooleanField):
                field.widget.attrs["class"] = "field"

    def clean_phone(self) -> str:
        phone = self.cleaned_data["phone"]
        if phone and not MOBILE.fullmatch(re.sub(r"\D", "", phone)):
            raise ValidationError(INVALID_MOBILE)
        return phone

    def client_data(self) -> dict:
        return {field: self.cleaned_data[field] for field in ("full_name", "phone", "document", "email", "notes")}

    def update_data(self) -> dict:
        """Celular y cédula no se muestran al editar: solo se cambian si se escribe un valor nuevo."""
        data = self.client_data()
        return {field: value for field, value in data.items() if field not in HIDDEN_ON_EDIT or value}


class NewClientForm(ClientForm):
    """Al crear, la autorización de tratamiento de datos es obligatoria (Ley 1581)."""

    consent = forms.BooleanField(
        label="El cliente autoriza el tratamiento de sus datos personales",
        error_messages={"required": "Sin la autorización del cliente no se pueden guardar sus datos."},
    )
