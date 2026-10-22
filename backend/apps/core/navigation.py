"""El marco de la aplicación (fase F1): qué ve cada membresía en la barra superior y la lateral.

Es la única definición de grupos e ítems, con su permiso de `roles.py`; las plantillas solo la pintan.
Un ítem sin `url_name` no tiene pantalla todavía: se muestra como "Próximamente" y nunca como enlace.
Ocultar un ítem es solo comodidad: cada vista exige su permiso en el servidor (`require_permission`).
"""

from dataclasses import dataclass

from django.http import HttpRequest
from django.urls import reverse

from apps.alerts.selectors import unread_count
from apps.core.shell_menus import account_menu, admin_panel, branch_menu, initials
from apps.tenancy.roles import role_has_permission


@dataclass(frozen=True)
class NavItem:
    label: str
    permission: str | None  # None: lo ve toda membresía activa
    url_name: str | None = None  # None: aún sin pantalla ("Próximamente")
    icon: str | None = None
    fragment: str = ""  # una parte de la página, como el formulario de gasto de la caja


@dataclass(frozen=True)
class NavGroup:
    title: str
    items: tuple[NavItem, ...]


SIDEBAR = (
    NavGroup(
        "Operación",
        (
            NavItem("Tablero", None, "home", "layout-dashboard"),
            NavItem("Agenda", "agenda.ver", icon="calendar"),
            NavItem("Comandas", "comandas.ver", "orders_board", "receipt"),
            NavItem("Caja", "caja.ver", "cash_register", "banknote"),
        ),
    ),
    NavGroup(
        "Clientes",
        (
            NavItem("Clientes", "clientes.ver", icon="users"),
            NavItem("Fiados", "fiados.ver", icon="notebook-pen"),
            NavItem("Reseñas", "clientes.ver", icon="star"),
        ),
    ),
    NavGroup(
        "Catálogo",
        (NavItem("Servicios", "servicios.ver", icon="tag"), NavItem("Inventario", "inventario.ver", icon="package")),
    ),
    NavGroup(
        "Análisis",
        (
            NavItem("Reportes", "reportes.ver", icon="chart-column"),
            NavItem("Comparativo de sedes", "sedes.ver", icon="git-compare-arrows"),
        ),
    ),
)

# Ninguna de estas pantallas existe todavía: todas salen como "Próximamente", cada una con su permiso.
ADMINISTRATION = (
    NavGroup(
        "Barbería",
        (
            NavItem("Datos de la barbería", "barberia.ver"),
            NavItem("Sedes", "sedes.gestionar"),
            NavItem("Horarios de atención", "barberia.ver"),
            NavItem("Medios de pago", "barberia.ver"),
        ),
    ),
    NavGroup(
        "Equipo",
        (
            NavItem("Barberos", "barberos.ver"),
            NavItem("Usuarios y roles", "usuarios.ver"),
            NavItem("Permisos por rol", "usuarios.ver"),
            NavItem("Comisiones", "barberos.ver"),
        ),
    ),
    NavGroup(
        "Catálogo y precios",
        (
            NavItem("Servicios", "servicios.editar"),
            NavItem("Precios por sede", "servicios.editar"),
            NavItem("Productos y categorías", "inventario.editar"),
            NavItem("Insumos por servicio", "inventario.editar"),
        ),
    ),
    NavGroup(
        "Clientes y fiados",
        (
            NavItem("Niveles de cliente", "barberia.ver"),
            NavItem("Reglas de fiado", "barberia.ver"),
            NavItem("Recordatorios", "barberia.ver"),
            NavItem("Reseñas", "barberia.ver"),
        ),
    ),
    NavGroup(
        "Seguridad y datos",
        (
            NavItem("Auditoría", "auditoria.ver"),
            NavItem("Seguridad de acceso", "usuarios.editar"),
            NavItem("Datos personales", "clientes.anonimizar"),
            NavItem("Exportar información", "reportes.exportar"),
        ),
    ),
    NavGroup(
        "Cuenta y plan",
        (
            NavItem("Plan y facturación", "barberia.editar"),
            NavItem("Integraciones", "barberia.editar"),
            NavItem("Textos legales", "barberia.ver"),
            NavItem("Soporte", "barberia.ver"),
        ),
    ),
)


# "+ Nuevo": solo las acciones que ya tienen pantalla, cada una con su permiso.
NEW_ACTIONS = (
    NavItem("Nueva comanda", "comandas.crear", "orders_new", "receipt"),
    NavItem("Cobro rápido", "comandas.cerrar", "orders_quick", "banknote"),
    NavItem("Registrar gasto", "caja.movimiento", "cash_register", "notebook-pen", fragment="gasto"),
)


def _module(url_name: str | None) -> str | None:
    """Las pantallas de un módulo comparten el prefijo del nombre: orders_board y orders_detail."""
    return url_name.split("_")[0] if url_name else None


def _visible(item: NavItem, role: str) -> bool:
    return item.permission is None or role_has_permission(role, item.permission)


def _item(item: NavItem, current_url_name: str | None) -> dict:
    return {
        "label": item.label,
        "icon": f"icons/{item.icon}.svg" if item.icon else None,
        "url": (reverse(item.url_name) + (f"#{item.fragment}" if item.fragment else "")) if item.url_name else None,
        "active": item.url_name is not None and _module(item.url_name) == _module(current_url_name),
    }


def visible_groups(groups: tuple[NavGroup, ...], role: str, current_url_name: str | None = None) -> list[dict]:
    """Los grupos con al menos un ítem que el rol puede ver, y solo esos ítems."""
    built = []
    for group in groups:
        items = [_item(item, current_url_name) for item in group.items if _visible(item, role)]
        if items:
            built.append({"title": group.title, "items": items})
    return built


def _membership_shell(request: HttpRequest, membership, current_url_name: str | None) -> dict:
    shop = membership.barbershop.trade_name
    scope = request.branch_scope
    return {
        "shop": {"name": shop, "initials": initials(shop)},
        "branches": branch_menu(membership, scope),
        "admin": admin_panel(membership, visible_groups(ADMINISTRATION, membership.role)),
        "sidebar": visible_groups(SIDEBAR, membership.role, current_url_name),
        "new_actions": [_item(item, None) for item in NEW_ACTIONS if _visible(item, membership.role)],
        # Las de la sede activa, o las de todas en "todas" (fase S4b de docs/sedes.md).
        "unread_alerts": unread_alerts(membership, scope),
    }


def unread_alerts(membership, scope) -> int | None:
    return unread_count(membership, scope=scope) if role_has_permission(membership.role, "alertas.ver") else None


def shell(request: HttpRequest) -> dict:
    """Context processor de la plantilla base.

    Sin membresía activa (varias barberías o ninguna) solo queda la cuenta, para poder cerrar sesión.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    membership = getattr(request, "membership", None)
    data = {"account": account_menu(user, membership, getattr(request, "branch_scope", None)), "shop": None}
    if membership is not None:
        current = request.resolver_match.url_name if request.resolver_match else None
        data |= _membership_shell(request, membership, current)
    return {"shell": data}
