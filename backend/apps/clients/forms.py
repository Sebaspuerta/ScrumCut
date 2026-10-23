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


class NewClientForm(ClientForm):
    """Al crear, la autorización de tratamiento de datos es obligatoria (Ley 1581)."""

    consent = forms.BooleanField(
        label="El cliente autoriza el tratamiento de sus datos personales",
        error_messages={"required": "Sin la autorización del cliente no se pueden guardar sus datos."},
    )
