"""Punto 9: cerrar sesión borra la sesión en el servidor, y se puede cerrar en todos los dispositivos."""

import pytest
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse

from apps.accounts.services import logout_all_devices
from apps.audit.models import AuditLog
from apps.tenancy.roles import Role
from tests.rls_support import back_to_test_role, become_production_role, postgres_only

pytestmark = pytest.mark.django_db


@pytest.fixture
def barber(make_shop, make_member):
    return make_member("barbero@example.com", make_shop("a"), Role.BARBER)


def _logged_in(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _is_authenticated(client: Client) -> bool:
    return client.get(reverse("home")).status_code == 200


def test_cerrar_en_todos_los_dispositivos(barber, make_member):
    laptop, phone = _logged_in(barber), _logged_in(barber)
    someone_else = _logged_in(make_member("otro@example.com", barber.memberships.get().barbershop, Role.BARBER))

    response = laptop.post(reverse("logout_everywhere"))

    assert (response.status_code, response.url) == (302, reverse("account_login"))
    assert not _is_authenticated(laptop) and not _is_authenticated(phone)
    assert _is_authenticated(someone_else)
    assert AuditLog.objects.filter(action="sesion.cerrar_todas", actor=barber).count() == 1


@postgres_only
def test_con_el_rol_de_produccion_y_barberia_activa_cierra_todo_y_audita_sin_barberia(barber):
    laptop, phone = _logged_in(barber), _logged_in(barber)
    become_production_role()

    response = laptop.post(reverse("logout_everywhere"))

    assert response.status_code == 302 and response.wsgi_request.barbershop is not None
    assert not _is_authenticated(phone)
    back_to_test_role()
    event = AuditLog.objects.get(action="sesion.cerrar_todas")
    assert (event.actor, event.barbershop) == (barber, None)


def test_si_la_auditoria_falla_la_version_de_sesion_no_cambia(barber, monkeypatch):
    def broken(**kwargs):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr("apps.accounts.services.record", broken)
    with pytest.raises(RuntimeError):
        logout_all_devices(barber)
    barber.refresh_from_db()
    assert barber.session_version == 0


def test_cerrar_en_todos_los_dispositivos_solo_por_post(barber):
    client = _logged_in(barber)
    assert client.get(reverse("logout_everywhere")).status_code == 405
    assert _is_authenticated(client)


def test_el_logout_invalida_la_sesion_en_el_servidor(barber):
    client = _logged_in(barber)
    session_key = client.cookies["sessionid"].value

    client.post(reverse("account_logout"))

    stolen = Client()
    stolen.cookies["sessionid"] = session_key
    assert not _is_authenticated(stolen)
    assert not Session.objects.filter(session_key=session_key).exists()


def test_el_logout_por_get_no_cierra_la_sesion(barber):
    client = _logged_in(barber)
    client.get(reverse("account_logout"))
    assert _is_authenticated(client)
