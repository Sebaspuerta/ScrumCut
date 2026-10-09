"""Escrituras de alertas.

Regla 48 portada de MAGNUS v1 (`alert_service.generate_system_alerts`). Defectos
corregidos: 25 y 26 (generar alertas y marcar vencidos ya no ocurre al leer: solo
en esta tarea), 30 y S11 (marcar exige `alertas.marcar`; `alertas.ver` solo lee) y
31 (la auditoría de "leída" queda en la misma transacción). No hay alertas manuales.
"""

from collections import Counter
from datetime import date
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.alerts.conditions import AlertKey, current_conditions
from apps.alerts.models import Alert, AlertType
from apps.audit.models import record
from apps.core.tenant_context import get_current_barbershop_id
from apps.receivables.services import mark_overdue
from apps.tenancy.models import Barbershop, Membership
from apps.tenancy.permissions import ensure_permission


def _active_barbershop() -> Barbershop:
    barbershop_id = get_current_barbershop_id()
    if barbershop_id is None:
        raise RuntimeError("generate_alerts necesita una barbería activa (tenant_context).")
    return Barbershop.objects.get(pk=barbershop_id)


def _open_alerts() -> dict[AlertKey, int]:
    """Alertas sin resolver, leídas o no, por clave."""
    rows = Alert.objects.filter(resolved_at__isnull=True).values_list("pk", "alert_type", "product_id", "receivable_id")
    return {(alert_type, product_id or receivable_id): pk for pk, alert_type, product_id, receivable_id in rows}


def _resolve_stale(open_alerts: dict[AlertKey, int], conditions: dict[AlertKey, str]) -> int:
    stale = [pk for key, pk in open_alerts.items() if key not in conditions]
    now = timezone.now()
    return Alert.objects.filter(pk__in=stale).update(resolved_at=now, updated_at=now)


def _create_missing(
    barbershop: Barbershop, open_alerts: dict[AlertKey, int], conditions: dict[AlertKey, str]
) -> list[Alert]:
    new_alerts = []
    for (alert_type, reference_id), message in conditions.items():
        if (alert_type, reference_id) in open_alerts:
            continue
        reference = "receivable_id" if alert_type == AlertType.OVERDUE_RECEIVABLE else "product_id"
        new_alerts.append(
            Alert(barbershop=barbershop, alert_type=alert_type, message=message, **{reference: reference_id})
        )
    # Si dos ejecuciones coinciden, la restricción única decide.
    Alert.objects.bulk_create(new_alerts, ignore_conflicts=True)
    return new_alerts


def generate_alerts(today: date) -> dict:
    """Tarea programada (comando `generar_alertas`) para la barbería activa. Idempotente.

    Marca los fiados vencidos, resuelve las alertas abiertas cuya condición
    desapareció y crea las que faltan.
    """
    barbershop = _active_barbershop()
    with transaction.atomic():
        overdue_marked = mark_overdue(today)
        conditions = current_conditions(today)
        open_alerts = _open_alerts()
        resolved = _resolve_stale(open_alerts, conditions)
        new_alerts = _create_missing(barbershop, open_alerts, conditions)
        summary = {
            "created": dict.fromkeys(AlertType.values, 0) | Counter(alert.alert_type for alert in new_alerts),
            "resolved": resolved,
            "overdue_marked": overdue_marked,
        }
        if new_alerts or resolved or overdue_marked:
            record(
                action="alertas.generar",
                entity=Alert._meta.label,
                barbershop=barbershop,
                after={**summary, "today": today.isoformat()},
            )
    return summary


def _read_snapshot(alert: Alert) -> dict:
    return {
        "read_at": alert.read_at.isoformat() if alert.read_at else None,
        "read_by": str(alert.read_by.public_id) if alert.read_by_id else None,
    }


def mark_as_read(membership: Membership, alert_public_id: UUID | str) -> Alert:
    """Si ya estaba leída o resuelta, no cambia nada ni audita."""
    ensure_permission(membership, "alertas.marcar")
    with transaction.atomic():
        alert = Alert.objects.select_for_update().get(public_id=alert_public_id)
        if alert.is_read or alert.resolved_at:
            return alert
        before = _read_snapshot(alert)
        alert.read_at = timezone.now()
        alert.read_by = membership
        alert.full_clean()
        alert.save(update_fields=["read_at", "read_by", "updated_at"])
        record(
            action="alerta.marcar_leida",
            entity=alert._meta.label,
            entity_id=str(alert.public_id),
            actor=membership.user,
            barbershop=membership.barbershop,
            before=before,
            after=_read_snapshot(alert),
        )
    return alert
