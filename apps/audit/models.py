from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Registro solo-agregar. No se edita ni se borra desde la aplicación.

    `barbershop` es opcional porque los eventos de plataforma (superadmin) no
    pertenecen a una barbería. Los listados para una barbería siempre filtran
    por ella en `selectors`.
    """

    barbershop = models.ForeignKey("tenancy.Barbershop", null=True, blank=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=64, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["barbershop", "created_at"])]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} · {self.action} · {self.entity}"

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None:
            raise PermissionError("El registro de auditoría no se modifica.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("El registro de auditoría no se borra.")


def record(
    *, action: str, entity: str, entity_id: str = "", actor=None, barbershop=None, before=None, after=None, request=None
) -> AuditLog:
    ip = None
    agent = ""
    if request is not None:
        # Detrás de Cloudflare la IP real llega en CF-Connecting-IP (Nginx solo acepta rangos de Cloudflare).
        ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR")
        agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    return AuditLog.objects.create(
        action=action,
        entity=entity,
        entity_id=entity_id,
        actor=actor,
        barbershop=barbershop,
        before=before,
        after=after,
        ip_address=ip,
        user_agent=agent,
    )
