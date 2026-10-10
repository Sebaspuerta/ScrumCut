"""Escrituras sobre la cuenta de una persona."""

from django.db import transaction
from django.db.models import F
from django.http import HttpRequest

from apps.accounts.models import User
from apps.audit.models import record
from apps.core.tenant_context import tenant_context


def logout_all_devices(user: User, request: HttpRequest | None = None) -> None:
    """Cierra toda sesión abierta del usuario, en cualquier dispositivo (ver `User._get_session_auth_hash`)."""
    with transaction.atomic():
        User.objects.filter(pk=user.pk).update(session_version=F("session_version") + 1)
        # Es un evento de la persona, no de la barbería activa: se audita como evento de plataforma.
        with tenant_context(None):
            record(
                action="sesion.cerrar_todas",
                entity=User._meta.label,
                entity_id=str(user.pk),
                actor=user,
                request=request,
            )
