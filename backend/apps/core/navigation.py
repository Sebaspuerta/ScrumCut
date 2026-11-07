"""El marco de la app de React: qué ve cada membresía en la barra lateral, Administración y "+ Nuevo".

Es la única definición de grupos e ítems, con su permiso de `roles.py`; la API (`apps.api.selectors`)
la entrega y React solo la pinta. Un ítem sin `app_path` no tiene pantalla todavía: sale como "Pronto" o
"Próximamente" y nunca como enlace. Ocultar un ítem es solo comodidad: cada vista de la API exige su permiso.
"""

from dataclasses import dataclass

from apps.alerts.selectors import unread_count
from apps.tenancy.roles import role_has_permission


@dataclass(frozen=True)
class NavItem:
    label: str
    permission: str | None  # None: lo ve toda membresía activa
    icon: str | None = None
    # Ruta dentro de la app de React (/app/...); None: aún sin pantalla.
    app_path: str | None = None


@dataclass(frozen=True)
class NavGroup:
    title: str
    items: tuple[NavItem, ...]


SIDEBAR = (
    NavGroup(
        "Operación",
        (
            NavItem("Tablero", None, "layout-dashboard", app_path="/"),
            NavItem("Agenda", "agenda.ver", icon="calendar"),
            NavItem("Comandas", "comandas.ver", "receipt", app_path="/comandas"),
            NavItem("Caja", "caja.ver", "banknote", app_path="/caja"),
        ),
    ),
    NavGroup(
        "Clientes",
        (
            NavItem("Clientes", "clientes.ver", "users", app_path="/clientes"),
            NavItem("Fiados", "fiados.ver", "notebook-pen", app_path="/fiados"),
            NavItem("Reseñas", "clientes.ver", icon="star"),
        ),
    ),
    NavGroup(
        "Catálogo",
        (
            NavItem("Servicios", "servicios.ver", icon="tag"),
            NavItem("Inventario", "inventario.ver", "package", app_path="/inventario"),
        ),
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
    NavItem("Nueva comanda", "comandas.crear", "receipt", app_path="/comandas?nueva=1"),
    NavItem("Cobro rápido", "comandas.cerrar", "banknote", app_path="/comandas?cobro=1"),
    NavItem("Registrar gasto", "caja.movimiento", "banknote", app_path="/caja?registrar=gasto"),
    NavItem("Nuevo cliente", "clientes.crear", "users", app_path="/clientes?nuevo=1"),
    NavItem("Abono a fiado", "fiados.abonar", "notebook-pen", app_path="/fiados"),
    NavItem("Nuevo producto", "inventario.crear", "package", app_path="/inventario?nuevo=1"),
)


def _visible(item: NavItem, role: str) -> bool:
    return item.permission is None or role_has_permission(role, item.permission)


def visible_items(groups: tuple[NavGroup, ...], role: str) -> list[tuple[NavGroup, list[NavItem]]]:
    """Los grupos con al menos un ítem que el rol puede ver, y solo esos ítems."""
    built = []
    for group in groups:
        items = [item for item in group.items if _visible(item, role)]
        if items:
            built.append((group, items))
    return built


def visible_actions(role: str) -> list[NavItem]:
    """Las acciones de "+ Nuevo" que el rol puede usar."""
    return [item for item in NEW_ACTIONS if _visible(item, role)]


def unread_alerts(membership, scope) -> int | None:
    return unread_count(membership, scope=scope) if role_has_permission(membership.role, "alertas.ver") else None
