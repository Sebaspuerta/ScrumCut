"""Lecturas de clientes. Los managers ya filtran por la barbería activa.

El perfil completo de la regla 47 (visitas, gasto, saldo) espera a sales y
receivables; aquí queda solo `client_status`, la regla pura que lo clasifica.
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.functions import Lower
from django.utils import timezone

from apps.clients.models import Client
from apps.clients.normalization import normalize_document, normalize_phone
from apps.core import crypto
from apps.tenancy.models import BarbershopSettings, Membership
from apps.tenancy.permissions import ensure_permission


class ClientStatus(models.TextChoices):
    DEBTOR = "debtor", "Deudor"
    NEW = "new", "Nuevo"
    FREQUENT = "frequent", "Frecuente"
    VIP = "vip", "VIP"
    INACTIVE = "inactive", "Inactivo"


def list_clients(membership: Membership, search: str | None = None) -> QuerySet[Client]:
    """Busca por nombre (contiene), teléfono (contiene los dígitos) o documento (exacto).

    No lista anonimizados; `get_client` sí los devuelve para el historial de ventas.
    """
    ensure_permission(membership, "clientes.ver")
    clients = Client.objects.filter(deleted_at__isnull=True, anonymized_at__isnull=True)
    term = (search or "").strip()
    if term:
        matches = Q(full_name__icontains=term) | Q(document_hash=crypto.keyed_hash(normalize_document(term)))
        digits = re.sub(r"\D", "", term)
        if digits:
            matches |= Q(phone__contains=digits)
        clients = clients.filter(matches)
    return clients.order_by(Lower("full_name"))


def get_client(membership: Membership, public_id: UUID | str) -> Client:
    """Nunca devuelve borrados. Lanza `Client.DoesNotExist`."""
    ensure_permission(membership, "clientes.ver")
    return Client.objects.get(public_id=public_id, deleted_at__isnull=True)


def find_duplicate(phone: str | None, document: str | None, *, exclude: Client | None = None) -> Client | None:
    """Regla 46: cliente vivo con el mismo teléfono o el mismo documento, ya normalizados."""
    normalized_phone = normalize_phone(phone)
    normalized_document = normalize_document(document)
    if not normalized_phone and not normalized_document:
        return None
    matches = Q()
    if normalized_phone:
        matches |= Q(phone=normalized_phone)
    if normalized_document:
        matches |= Q(document_hash=crypto.keyed_hash(normalized_document))
    candidates = Client.objects.filter(matches, deleted_at__isnull=True)
    if exclude is not None:
        candidates = candidates.exclude(pk=exclude.pk)
    return candidates.order_by("pk").first()


def client_status(
    visits: int,
    spent: Decimal,
    last_visit: datetime | None,
    balance: Decimal,
    settings: BarbershopSettings,
    *,
    now: datetime | None = None,
) -> ClientStatus:
    """Regla 47 (`client_service.get_client_profile`) con los umbrales de la barbería.

    El saldo pendiente manda; la inactividad reemplaza cualquier otro estado
    cuando no hay deuda.
    """
    now = now or timezone.now()
    if balance > 0:
        return ClientStatus.DEBTOR
    if last_visit is not None and last_visit < now - timedelta(days=settings.inactive_after_days):
        return ClientStatus.INACTIVE
    if visits == 0:
        return ClientStatus.NEW
    if spent >= settings.vip_min_spent or visits >= settings.vip_min_visits:
        return ClientStatus.VIP
    if visits >= settings.frequent_min_visits:
        return ClientStatus.FREQUENT
    return ClientStatus.NEW
