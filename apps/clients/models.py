"""Clientes de cada barbería.

Portado de MAGNUS v1 (`models/client.py`) según `docs/migracion-magnus.md`:
el documento se guarda cifrado con una huella para detectar duplicados, la
unicidad de teléfono y documento vive en la base y cada cliente lleva su
autorización de tratamiento de datos (Ley 1581 de 2012).
"""

from django.db import models

from apps.clients.normalization import normalize_document, normalize_name
from apps.core import crypto
from apps.core.models import SoftDeleteModel, TenantScopedModel

_ALIVE = models.Q(deleted_at__isnull=True)


class Client(TenantScopedModel, SoftDeleteModel):
    full_name = models.CharField("nombre completo", max_length=120)
    phone = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField("correo", blank=True)
    birth_date = models.DateField("fecha de nacimiento", null=True, blank=True)
    notes = models.TextField("notas", blank=True)
    # Documento normalizado cifrado con Fernet; `document_hash` es su HMAC para buscar sin descifrar.
    document_number_encrypted = models.TextField(blank=True, editable=False)
    document_hash = models.CharField(max_length=64, blank=True, editable=False)
    data_consent_at = models.DateTimeField("autorización de datos")
    data_policy_version = models.CharField("versión de la política de datos", max_length=20)
    # Nombre normalizado (normalize_name) para avisar de posibles duplicados.
    name_key = models.CharField(max_length=120, blank=True, editable=False)
    # Supresión de datos (Ley 1581): irreversible; el registro queda para que las ventas cuadren.
    anonymized_at = models.DateTimeField("anonimizado", null=True, blank=True, editable=False)

    class Meta:
        indexes = [models.Index(fields=["barbershop", "name_key"], name="ix_client_name_key")]
        constraints = [
            models.UniqueConstraint(
                fields=["barbershop", "document_hash"],
                condition=_ALIVE & ~models.Q(document_hash=""),
                name="uq_client_document_per_barbershop",
                violation_error_message="Ya existe un cliente con ese documento.",
            ),
            models.UniqueConstraint(
                fields=["barbershop", "phone"],
                condition=_ALIVE & ~models.Q(phone=""),
                name="uq_client_phone_per_barbershop",
                violation_error_message="Ya existe un cliente con ese teléfono.",
            ),
            models.CheckConstraint(
                condition=~models.Q(data_policy_version=""), name="ck_client_policy_version_present"
            ),
        ]

    def __str__(self) -> str:
        return self.full_name

    @property
    def is_anonymized(self) -> bool:
        return self.anonymized_at is not None

    def set_full_name(self, raw: str | None) -> None:
        self.full_name = (raw or "").strip()
        self.name_key = normalize_name(self.full_name)

    @property
    def document_number(self) -> str:
        if not self.document_number_encrypted:
            return ""
        return crypto.decrypt(self.document_number_encrypted)

    def set_document(self, raw: str | None) -> None:
        normalized = normalize_document(raw)
        if normalized:
            self.document_number_encrypted = crypto.encrypt(normalized)
            self.document_hash = crypto.keyed_hash(normalized)
        else:
            self.document_number_encrypted = ""
            self.document_hash = ""
