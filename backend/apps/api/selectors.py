"""Lecturas de la API del marco: reúnen lo que ya calculan la navegación, los menús y el alcance de sede.

Ninguna decide permisos ni sedes por su cuenta: usan `roles.py`, `navigation.py` y `BranchScope`.
"""

from apps.accounts.models import User
from apps.core.navigation import (
    ADMINISTRATION,
    SIDEBAR,
    NavGroup,
    NavItem,
    item_url,
    unread_alerts,
    visible_actions,
    visible_items,
)
from apps.core.shell_menus import admin_summary, branch_menu, initials
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Membership
from apps.tenancy.roles import ALL_PERMISSIONS, role_has_permission

# Estado de un ítem: con pantalla, sin pantalla en la barra lateral y sin pantalla en Administración.
LINK, SOON, COMING = "enlace", "pronto", "proximamente"


def branch_state(membership: Membership, scope: BranchScope) -> dict:
    """La sede actual y las que puede elegir, tal como las arma el selector de la barra superior."""
    menu = branch_menu(membership, scope)
    return {
        "mode": scope.mode,
        "current_label": menu["current"],
        "options": menu["options"],
        "can_view_all": menu["all"] is not None,
        "can_manage": menu["manage"],
    }


def _user(user: User) -> dict:
    name = user.full_name or user.email
    return {"email": user.email, "name": name, "initials": initials(name), "theme": user.theme}


def me(user: User, membership: Membership | None, scope: BranchScope | None) -> dict:
    """Sin membresía activa (ninguna barbería o varias) solo vuelve la persona."""
    if membership is None or scope is None:
        return {"user": _user(user), "barbershop": None, "role": None, "permissions": [], "branch": None}
    shop = membership.barbershop.trade_name
    return {
        "user": _user(user),
        "barbershop": {"name": shop, "initials": initials(shop), "timezone": membership.barbershop.timezone},
        "role": {"code": membership.role, "label": membership.get_role_display()},
        "permissions": sorted(code for code in ALL_PERMISSIONS if role_has_permission(membership.role, code)),
        "branch": branch_state(membership, scope),
    }


def _nav_item(item: NavItem, without_screen: str) -> dict:
    url = item_url(item)
    return {
        "label": item.label,
        "icon": item.icon,
        "url": url,
        "app_path": item.app_path,
        "status": LINK if url else without_screen,
    }


def _groups(groups: tuple[NavGroup, ...], role: str, without_screen: str) -> list[dict]:
    return [
        {"title": group.title, "items": [_nav_item(item, without_screen) for item in items]}
        for group, items in visible_items(groups, role)
    ]


def _summary(membership: Membership) -> dict:
    """El resumen del panel de Administración; cada dato es None sin su permiso."""
    summary = admin_summary(membership)
    audit = summary.get("audit")
    return {
        "branches": summary.get("branches"),
        "members": summary.get("members"),
        "can_see_audit": audit is not None,
        "last_change": audit["event"] if audit else None,
    }


def navigation(membership: Membership, scope: BranchScope) -> dict:
    """La barra lateral ("Pronto" sin pantalla), Administración ("Próximamente"), "+ Nuevo" y las alertas."""
    role = membership.role
    administration = _groups(ADMINISTRATION, role, COMING)
    return {
        "sidebar": _groups(SIDEBAR, role, SOON),
        "administration": administration,
        "administration_summary": _summary(membership) if administration else None,
        "new_actions": [_nav_item(item, SOON) for item in visible_actions(role)],
        "unread_alerts": unread_alerts(membership, scope),
    }
