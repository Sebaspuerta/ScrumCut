"""Los datos de la barra superior de la app de React: selector de sede y resumen de Administración.

Cada dato sale de un selector y se muestra solo con su permiso. Las sedes salen del alcance de
la petición (`BranchScope.choices`), nunca de un filtro escrito aquí.
"""

from apps.audit.selectors import latest_event
from apps.tenancy.branch_scope import ALL, BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import role_has_permission
from apps.tenancy.selectors import active_member_count, plan_usage

ALL_BRANCHES = "Todas las sedes"


def initials(text: str) -> str:
    return "".join(word[0] for word in text.split()[:2]).upper()


def scope_label(scope: BranchScope | None) -> str:
    if scope is None:
        return ""
    return scope.branch.name if scope.branch else ALL_BRANCHES


def branch_menu(membership: Membership, scope: BranchScope) -> dict:
    """La sede actual, las que puede elegir, "Todas" con sedes.ver y "Gestionar sedes" con sedes.gestionar."""
    role = membership.role
    options = [
        {"token": str(branch.public_id), "label": branch.name, "current": branch == scope.branch}
        for branch in scope.choices()
    ]
    everything = {"token": ALL, "current": scope.is_all} if role_has_permission(role, "sedes.ver") else None
    return {
        "current": scope_label(scope),
        "options": options,
        "all": everything,
        "manage": role_has_permission(role, "sedes.gestionar"),
    }


def _branches_summary(membership: Membership) -> dict:
    usage = plan_usage(membership.barbershop)
    percent = min(100, usage["active"] * 100 // usage["limit"])
    return {**usage, "bar": str(percent)}


def _audit_summary(membership: Membership) -> dict:
    event = latest_event(membership)
    if event is None:
        return {"event": None}
    actor = event.actor.email if event.actor_id else "Plataforma"
    return {"event": {"action": event.action, "entity": event.entity, "actor": actor, "at": event.created_at}}


def admin_summary(membership: Membership) -> dict:
    """Lo que muestra el panel de Administración a la derecha, cada dato solo con su permiso."""
    role = membership.role
    summary = {}
    if role_has_permission(role, "sedes.ver"):
        summary["branches"] = _branches_summary(membership)
    if role_has_permission(role, "usuarios.ver"):
        summary["members"] = active_member_count(membership.barbershop)
    if role_has_permission(role, "auditoria.ver"):
        summary["audit"] = _audit_summary(membership)
    return summary
