"""Punto 10: el campo trampa frena bots en el registro y la recuperación sin delatarse."""

import logging

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.forms import HONEYPOT_FIELD, ScrumCutSignupForm
from apps.accounts.models import User
from apps.tenancy.roles import Role
from tests.security.conftest import sign_up

pytestmark = pytest.mark.django_db

BOT = {HONEYPOT_FIELD: "https://spam.example"}


def _redirect(response) -> tuple[int, str]:
    return response.status_code, response.url


def test_el_campo_trampa_no_se_ve_ni_se_enfoca(legal_documents):
    attrs = ScrumCutSignupForm().fields[HONEYPOT_FIELD].widget.attrs
    assert attrs == {"hidden": True, "tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}


def test_un_bot_no_crea_cuenta_ni_recibe_correo_y_ve_la_misma_respuesta(client, legal_documents, caplog):
    with caplog.at_level(logging.WARNING, logger="apps.accounts.forms"):
        bot = sign_up(client, email="bot@example.com", **BOT)

    assert not User.objects.filter(email="bot@example.com").exists()
    assert mail.outbox == []
    assert "127.0.0.1" in caplog.text and "bot@example.com" not in caplog.text

    person = sign_up(client, email="persona@example.com")
    assert User.objects.filter(email="persona@example.com").exists() and len(mail.outbox) == 1
    assert _redirect(bot) == _redirect(person)


def test_la_recuperacion_con_el_campo_lleno_no_envia_correo(client, make_shop, make_member):
    make_member("cajero@example.com", make_shop("a"), Role.CASHIER)
    url = reverse("account_reset_password")

    bot = client.post(url, {"email": "cajero@example.com", **BOT})
    assert mail.outbox == []

    person = client.post(url, {"email": "cajero@example.com", HONEYPOT_FIELD: ""})
    assert len(mail.outbox) == 1
    assert _redirect(bot) == _redirect(person)
