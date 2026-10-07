"""Escrituras de clientes.

Regla 46 portada de MAGNUS v1 (`services/client_service.py`): no hay dos clientes
vivos con el mismo teléfono o documento. La auditoría nunca guarda el documento
en claro: solo si el cliente tiene uno y si cambió.

Igual que en catalog y staff: un objeto inexistente, de otra barbería o borrado
lanza `DoesNotExist`; los datos inválidos, `ValidationError`.
"""

from datetime import date, datetime
from typing import TypedDict
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import record
from apps.clients.models import Client
from apps.clients.normalization import normalize_phone
from apps.tenancy.models import Membership
from apps.tenancy.permissions import ensure_permission

DUPLICATE_CLIENT = "Ya existe un cliente con ese teléfono o documento."
POSSIBLE_DUPLICATE = "Ya hay un cliente con ese nombre. Confirma si es otra persona."
ANONYMIZED_LOCKED = "Un cliente anonimizado no se edita."
ANONYMIZED_NAME = "Cliente anonimizado"


class ClientData(TypedDict, total=False):
    full_name: str
    phone: str
    email: str
    birth_date: date | None
    notes: str
    document: str


def _audit(actor: Membership, action: str, client: Client, *, before: dict | None, after: dict | None) -> None:
    record(
        action=action,
        entity=client._meta.label,
        entity_id=str(client.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        before=before,
        after=after,
    )


def _snapshot(client: Client) -> dict:
    return {
        "full_name": client.full_name,
        "phone": client.phone,
        "email": client.email,
        "birth_date": client.birth_date.isoformat() if client.birth_date else None,
        "notes": client.notes,
        "has_document": bool(client.document_hash),
        "data_consent_at": client.data_consent_at.isoformat() if client.data_consent_at else None,
        "data_policy_version": client.data_policy_version,
        "deleted_at": client.deleted_at.isoformat() if client.deleted_at else None,
    }


def _apply(client: Client, data: ClientData) -> None:
    unknown = set(data) - set(ClientData.__annotations__)
    if unknown:
        raise TypeError(f"Campos desconocidos: {sorted(unknown)}")
    if "full_name" in data:
        client.set_full_name(data["full_name"])
    if "notes" in data:
        client.notes = (data["notes"] or "").strip()
    if "phone" in data:
        client.phone = normalize_phone(data["phone"])
    if "email" in data:
        client.email = (data["email"] or "").strip().lower()
    if "birth_date" in data:
        client.birth_date = data["birth_date"]
    if "document" in data:
        client.set_document(data["document"])


def _conflicting_client(client: Client) -> Client | None:
    """Otro cliente vivo con el mismo teléfono o huella de documento (ya normalizados)."""
    matches = Q()
    if client.phone:
        matches |= Q(phone=client.phone)
    if client.document_hash:
        matches |= Q(document_hash=client.document_hash)
    if not matches:
        return None
    return Client.objects.filter(matches, deleted_at__isnull=True).exclude(pk=client.pk).order_by("pk").first()


def _duplicate_error(existing: Client) -> ValidationError:
    return ValidationError(
        DUPLICATE_CLIENT, code="duplicate_client", params={"existing_client": str(existing.public_id)}
    )


def _possible_duplicates(client: Client) -> list[Client]:
    """Otros clientes vivos, no anonimizados, con el mismo nombre normalizado."""
    if not client.name_key:
        return []
    candidates = Client.objects.filter(name_key=client.name_key, deleted_at__isnull=True, anonymized_at__isnull=True)
    return list(candidates.exclude(pk=client.pk).order_by("pk"))


def _save_validated(client: Client) -> None:
    if existing := _conflicting_client(client):
        raise _duplicate_error(existing)
    try:
        client.full_clean()
        with transaction.atomic():
            client.save()
    except (ValidationError, IntegrityError) as exc:
        # La restricción de la base es la última palabra (también ante solicitudes simultáneas).
        existing = _conflicting_client(client)
        if existing is not None:
            raise _duplicate_error(existing) from exc
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(DUPLICATE_CLIENT, code="duplicate_client") from exc


def _validate_consent(data_consent_at: datetime | None) -> None:
    if data_consent_at is None:
        raise ValidationError({"data_consent_at": "Se requiere la autorización de tratamiento de datos."})
    if timezone.is_naive(data_consent_at):
        raise ValidationError({"data_consent_at": "La fecha de autorización debe incluir zona horaria."})
    if data_consent_at > timezone.now():
        raise ValidationError({"data_consent_at": "La fecha de autorización no puede estar en el futuro."})


def create_client(
    membership: Membership,
    data: ClientData,
    *,
    data_consent_at: datetime | None,
    data_policy_version: str,
    force: bool = False,
) -> Client:
    """Regla 46.

    - Teléfono o documento exactos de otro cliente vivo: falla siempre, con el
      `public_id` del existente (código `duplicate_client`).
    - Mismo nombre normalizado: posible duplicado. Falla con los `public_id` de los
      candidatos (código `possible_duplicate`) salvo que `force=True` confirme que
      es otra persona.
    """
    ensure_permission(membership, "clientes.crear")
    _validate_consent(data_consent_at)
    with transaction.atomic():
        client = Client(
            barbershop_id=membership.barbershop_id,
            data_consent_at=data_consent_at,
            data_policy_version=(data_policy_version or "").strip(),
        )
        _apply(client, data)
        if existing := _conflicting_client(client):
            raise _duplicate_error(existing)
        if not force and (similar := _possible_duplicates(client)):
            raise ValidationError(
                POSSIBLE_DUPLICATE,
                code="possible_duplicate",
                params={"possible_duplicates": [str(other.public_id) for other in similar]},
            )
        _save_validated(client)
        _audit(membership, "cliente.crear", client, before=None, after=_snapshot(client))
    return client


def update_client(membership: Membership, public_id: UUID | str, data: ClientData) -> Client:
    """Solo cambia las claves presentes en `data`. `document=""` quita el documento."""
    ensure_permission(membership, "clientes.editar")
    with transaction.atomic():
        client = Client.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)
        if client.is_anonymized:
            raise ValidationError(ANONYMIZED_LOCKED)
        before = _snapshot(client)
        previous_hash = client.document_hash
        _apply(client, data)
        _save_validated(client)
        after = _snapshot(client)
        document_changed = client.document_hash != previous_hash
        if document_changed:
            after["document_changed"] = True
        if after != before:
            _audit(membership, "cliente.editar", client, before=before, after=after)
    return client


def soft_delete_client(membership: Membership, public_id: UUID | str) -> Client:
    ensure_permission(membership, "clientes.eliminar")
    with transaction.atomic():
        client = Client.objects.select_for_update().get(public_id=public_id, deleted_at__isnull=True)
        before = _snapshot(client)
        client.soft_delete(by=membership.user)
        _audit(membership, "cliente.eliminar", client, before=before, after=_snapshot(client))
    return client


def anonymize_client(membership: Membership, public_id: UUID | str) -> Client:
    """Supresión de datos personales (Ley 1581). Irreversible; solo el dueño.

    Conserva el registro (también si estaba borrado) para que ventas y fiados
    sigan cuadrando. La auditoría no guarda ningún dato personal.
    """
    ensure_permission(membership, "clientes.anonimizar")
    with transaction.atomic():
        client = Client.objects.select_for_update().get(public_id=public_id)
        if client.is_anonymized:
            raise ValidationError("Este cliente ya fue anonimizado.")
        client.full_name = ANONYMIZED_NAME
        client.name_key = ""
        client.phone = ""
        client.email = ""
        client.set_document("")
        client.birth_date = None
        client.notes = ""
        client.anonymized_at = timezone.now()
        client.full_clean()
        client.save()
        _audit(
            membership,
            "cliente.anonimizar",
            client,
            before={"anonymized_at": None},
            after={"anonymized_at": client.anonymized_at.isoformat()},
        )
    return client
