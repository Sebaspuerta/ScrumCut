"""El panel de notificaciones: las alertas sin resolver del alcance, agrupadas en Hoy y Anteriores.

Solo lee, con `alerts.selectors.list_alerts` (permiso alertas.ver y alcance de sede); generar y
resolver alertas sigue siendo de la tarea programada.
"""

from zoneinfo import ZoneInfo

from apps.alerts.models import Alert
from apps.alerts.selectors import list_alerts, unread_count
from apps.sales.selectors import local_today
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership

PANEL_SIZE = 20
TODAY, EARLIER = "Hoy", "Anteriores"


def alert_item(alert: Alert) -> dict:
    """Una alerta como la ven el panel de notificaciones y el tablero."""
    return {
        "id": alert.public_id,
        "kind": alert.alert_type,
        "kind_label": alert.get_alert_type_display(),
        "message": alert.message,
        "branch": alert.branch.name,
        "created_at": alert.created_at,
        "unread": alert.read_at is None,
    }


def notifications(membership: Membership, *, scope: BranchScope) -> dict:
    """Las no leídas primero y las más recientes arriba; hasta `PANEL_SIZE`. Sin alertas, grupos vacíos."""
    alerts = list(list_alerts(membership, scope=scope, page_size=PANEL_SIZE))
    tz, today = ZoneInfo(membership.barbershop.timezone), local_today(membership)
    groups = {TODAY: [], EARLIER: []}
    for alert in alerts:
        groups[TODAY if alert.created_at.astimezone(tz).date() == today else EARLIER].append(alert_item(alert))
    return {
        "unread": unread_count(membership, scope=scope),
        "groups": [{"title": title, "items": items} for title, items in groups.items() if items],
    }
