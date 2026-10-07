"""Bases para todas las tablas de negocio."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.tenant_context import get_current_barbershop_id


class TimeStampedModel(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_current_barbershop(self) -> "TenantQuerySet":
        barbershop_id = get_current_barbershop_id()
        if barbershop_id is None:
            # Sin barbería activa no se devuelve nada: fallar cerrado.
            return self.none()
        return self.filter(barbershop_id=barbershop_id)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> TenantQuerySet:
        return super().get_queryset().for_current_barbershop()


class TenantScopedModel(TimeStampedModel):
    """Toda tabla de negocio hereda de aquí.

    - `objects` filtra siempre por la barbería activa.
    - `unscoped` existe solo para tareas de plataforma y debe usarse a propósito.
    - Al crear, si no se indica barbería, se toma la activa; sin barbería activa, falla.
    """

    barbershop = models.ForeignKey("tenancy.Barbershop", on_delete=models.PROTECT, db_index=True)

    objects = TenantManager()
    unscoped = models.Manager()  # noqa: DJ012 — los managers van juntos a propósito

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        if self.barbershop_id is None:
            current = get_current_barbershop_id()
            if current is None:
                raise RuntimeError("No hay barbería activa: no se puede guardar un registro de negocio.")
            self.barbershop_id = current
        super().save(*args, **kwargs)


class SoftDeleteModel(models.Model):
    """Borrado lógico para catálogo, personal y clientes. Nunca para movimientos."""

    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, by) -> None:
        self.deleted_at = timezone.now()
        self.deleted_by = by
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    def delete(self, *args, **kwargs):
        raise PermissionError("Borrado físico deshabilitado: usa soft_delete().")


class AppendOnlyQuerySet(TenantQuerySet):
    def update(self, **kwargs):
        raise PermissionError("Tabla solo-agregar: no se modifica.")

    def delete(self):
        raise PermissionError("Tabla solo-agregar: no se borra.")


class AppendOnlyModel(TenantScopedModel):
    """Libros de movimientos (comisiones, inventario, caja): se agregan, nunca se editan ni se borran.

    Una corrección es un movimiento nuevo que compensa al anterior.
    """

    objects = TenantManager.from_queryset(AppendOnlyQuerySet)()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None:
            raise PermissionError(f"{self._meta.verbose_name} no se modifica: registra un movimiento nuevo.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(f"{self._meta.verbose_name} no se borra.")
