"""Documentos legales versionados y evidencia de aceptación (Ley 1581 de 2012)."""

from django.conf import settings
from django.db import models


class LegalDocument(models.Model):
    class Kind(models.TextChoices):
        DATA_POLICY = "data_policy", "Política de tratamiento de datos"
        PRIVACY_NOTICE = "privacy_notice", "Aviso de privacidad"
        TERMS = "terms", "Términos y condiciones"
        DATA_PROCESSING = "data_processing", "Contrato de transmisión de datos"
        COOKIES = "cookies", "Política de cookies"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    version = models.CharField(max_length=20)
    body = models.TextField()
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["kind", "version"], name="uq_legal_kind_version")]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} v{self.version}"


class Acceptance(models.Model):
    """Quién aceptó qué versión, cuándo y desde dónde. Solo-agregar."""

    document = models.ForeignKey(LegalDocument, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    barbershop = models.ForeignKey("tenancy.Barbershop", null=True, blank=True, on_delete=models.PROTECT)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user} aceptó {self.document}"

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None:
            raise PermissionError("Una aceptación registrada no se modifica.")
        super().save(*args, **kwargs)
