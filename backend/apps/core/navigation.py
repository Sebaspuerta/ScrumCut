"""Barra superior y menú lateral: qué enlaces ve cada membresía, según `roles.py`.

Es la única lista de módulos de la interfaz. Ocultar un enlace es solo comodidad:
cada vista exige su permiso en el servidor (`require_permission`).
"""

from dataclasses import dataclass

from django.http import HttpRequest
from django.urls import reverse

from apps.alerts.selectors import unread_count
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.roles import role_has_permission


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    icon: str
    permission: str | None  # None: lo ve toda membresía activa
    url_name: str | None = None  # None: el módulo aún no tiene pantalla


ADMIN_ITEMS = (
    NavItem("barberos", "Gestión de barberos", "user-cog", "barberos.ver"),
    NavItem("usuarios", "Usuarios y roles", "shield-check", "usuarios.ver"),
    NavItem("auditoria", "Auditoría", "history", "auditoria.ver"),
    NavItem("ajustes", "Ajustes", "settings", "barberia.ver"),
)

MODULE_ITEMS = (
    NavItem("tablero", "Tablero", "layout-dashboard", None, "home"),
    NavItem("comandas", "Comandas", "receipt", "comandas.ver"),
    NavItem("caja", "Caja", "banknote", "caja.ver"),
    NavItem("clientes", "Clientes", "users", "clientes.ver"),
    NavItem("servicios", "Servicios", "tag", "servicios.ver"),
    NavItem("inventario", "Inventario", "package", "inventario.ver"),
    NavItem("fiados", "Fiados", "notebook-pen", "fiados.ver"),
    NavItem("reportes", "Reportes", "chart-column", "reportes.ver"),
    NavItem("alertas", "Alertas", "bell", "alertas.ver"),
)


def initials(text: str) -> str:
    return "".join(word[0] for word in text.split()[:2]).upper()


def _links(items: tuple[NavItem, ...], role: str, current_url_name: str | None) -> list[dict]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "icon": f"icons/{item.icon}.svg",
            "url": reverse(item.url_name) if item.url_name else None,
            "active": item.url_name is not None and item.url_name == current_url_name,
        }
        for item in items
        if item.permission is None or role_has_permission(role, item.permission)
    ]


def _account(user, membership) -> dict:
    name = user.full_name or user.email
    return {"name": name, "initials": initials(name), "role": membership.get_role_display() if membership else ""}


def _membership_shell(membership, current_url_name: str | None, *, scope: BranchScope) -> dict:
    role = membership.role
    shop = membership.barbershop.trade_name
    return {
        "shop": {"name": shop, "initials": initials(shop)},
        "admin_links": _links(ADMIN_ITEMS, role, current_url_name),
        "module_links": _links(MODULE_ITEMS, role, current_url_name),
        "can_export": role_has_permission(role, "reportes.exportar"),
        # Las de la sede activa, o las de todas en "todas" (fase S4b de docs/sedes.md).
        "unread_alerts": unread_count(membership, scope=scope) if role_has_permission(role, "alertas.ver") else None,
    }


def shell(request: HttpRequest) -> dict:
    """Context processor de la plantilla base.

    Sin membresía activa (varias barberías o ninguna) solo queda la cuenta, para poder cerrar sesión.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    membership = getattr(request, "membership", None)
    data = {"account": _account(user, membership), "shop": None, "admin_links": [], "module_links": []}
    if membership is not None:
        current = request.resolver_match.url_name if request.resolver_match else None
        data |= _membership_shell(membership, current, scope=request.branch_scope)
    return {"shell": data}
