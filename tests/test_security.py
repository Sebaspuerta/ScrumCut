import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from apps.audit.models import record
from apps.tenancy.roles import Role
from config import env

pytestmark = pytest.mark.django_db


def test_un_secreto_ausente_detiene_el_arranque(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ImproperlyConfigured):
        env.require("SECRET_KEY")


def test_la_salud_no_revela_version_ni_modo(client):
    response = client.get(reverse("health"))
    assert response.json() == {"status": "ok"}


def test_el_dueno_sin_2fa_es_enviado_a_configurarlo(client, make_shop, make_member):
    user = make_member("dueno@example.com", make_shop("a"), Role.OWNER)
    client.force_login(user)
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert response.url == reverse("mfa_activate_totp")


def test_el_barbero_entra_sin_2fa_obligatorio(client, make_shop, make_member):
    user = make_member("barbero@example.com", make_shop("a"), Role.BARBER)
    client.force_login(user)
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert response.wsgi_request.barbershop.slug == "a"


def test_la_sesion_no_entrega_tokens_al_navegador(client, make_shop, make_member):
    user = make_member("barbero@example.com", make_shop("a"), Role.BARBER)
    client.force_login(user)
    response = client.get(reverse("home"))
    assert response.cookies.get("sessionid") is None or response.cookies["sessionid"]["httponly"]
    assert "token" not in response.content.decode().lower()


def test_cinco_intentos_fallidos_bloquean_el_login(client, make_shop, make_member):
    make_member("cajero@example.com", make_shop("a"), Role.CASHIER, password="clave-correcta-2026")
    url = reverse("account_login")
    for _ in range(5):
        client.post(url, {"login": "cajero@example.com", "password": "incorrecta"})
    response = client.post(url, {"login": "cajero@example.com", "password": "clave-correcta-2026"})
    # Aun con la contraseña correcta, la sesión no se abre durante el bloqueo.
    assert response.status_code != 302
    assert "_auth_user_id" not in client.session


def test_la_auditoria_no_se_modifica_ni_se_borra():
    entry = record(action="prueba", entity="test")
    entry.action = "alterada"
    with pytest.raises(PermissionError):
        entry.save()
    with pytest.raises(PermissionError):
        entry.delete()
