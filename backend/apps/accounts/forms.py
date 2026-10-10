"""Formularios de allauth con campo trampa y, en el registro, la autorización de datos (Ley 1581 de 2012)."""

import logging

from allauth.account.adapter import get_adapter
from allauth.account.forms import ResetPasswordForm, SignupForm
from django import forms
from django.db import transaction
from django.http import HttpRequest
from django.template.loader import render_to_string

from apps.core.http import client_ip
from apps.legal.services import accept_signup_documents

logger = logging.getLogger(__name__)

HONEYPOT_FIELD = "sitio_web"


class HoneypotMixin:
    """Campo trampa que una persona no ve y un bot suele llenar.

    Se oculta con el atributo `hidden` y no con CSS: la CSP estricta bloquea los
    estilos en línea, y un campo trampa visible confundiría a las personas.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields[HONEYPOT_FIELD] = forms.CharField(
            required=False,
            label="",
            widget=forms.TextInput(
                attrs={"hidden": True, "tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}
            ),
        )

    def caught_bot(self, request: HttpRequest) -> bool:
        if not self.cleaned_data.get(HONEYPOT_FIELD):
            return False
        # Sin datos del formulario en el log: solo cuál fue y desde dónde.
        logger.warning("%s descartado por el campo trampa; IP %s", type(self).__name__, client_ip(request))
        return True


class ScrumCutSignupForm(HoneypotMixin, SignupForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["legal_consent"] = forms.BooleanField(
            required=True, label=render_to_string("legal/consent_label.html")
        )

    def try_save(self, request: HttpRequest):
        if self.caught_bot(request):
            # La misma respuesta de un registro real: el bot no aprende nada.
            return None, get_adapter().respond_email_verification_sent(request, None)
        return super().try_save(request)

    def save(self, request: HttpRequest):
        with transaction.atomic():
            user = super().save(request)
            accept_signup_documents(user, request)
        return user


class ScrumCutResetPasswordForm(HoneypotMixin, ResetPasswordForm):
    def save(self, request: HttpRequest, **kwargs) -> str:
        if self.caught_bot(request):
            return self.cleaned_data["email"]
        return super().save(request, **kwargs)
