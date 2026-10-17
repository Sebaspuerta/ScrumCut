"""Formularios de sedes: el cambio de sede y la base de los formularios que escriben con sede."""

from django import forms
from django.core.exceptions import ValidationError

from apps.tenancy.branch_scope import BranchScope

CROSS_TAB_MESSAGE = "Cambiaste de sede en otra pestaña; revisa antes de guardar"


class BranchSwitchForm(forms.Form):
    """Solo el formato: qué sede se puede elegir lo decide `tenancy.services.choose_branch`."""

    sede = forms.CharField(max_length=40)
    next = forms.CharField(required=False, max_length=2000)


class BranchBoundForm(forms.Form):
    """Base de todo formulario que escribe con sede (docs/sedes.md, "Pestañas cruzadas").

    Lleva oculta la sede con la que se abrió y rechaza el envío si ya no es la sede activa,
    por ejemplo porque se cambió de sede en otra pestaña.
    """

    sede_origen = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, branch_scope: BranchScope, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.branch_scope = branch_scope
        self.fields["sede_origen"].initial = branch_scope.token

    def clean_sede_origen(self) -> str:
        origin = self.cleaned_data["sede_origen"]
        if origin != self.branch_scope.token:
            raise ValidationError(CROSS_TAB_MESSAGE, code="cross_tab")
        return origin
