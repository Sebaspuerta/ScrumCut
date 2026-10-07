"""Roles por barbería y matriz de permisos.

La matriz vive en código (versionada y probada), no en tablas editables: un
permiso cambiado en la base de datos no deja rastro en el repositorio.
"""

from django.db import models


class Role(models.TextChoices):
    OWNER = "owner", "Dueño"
    ADMIN = "admin", "Administrador"
    CASHIER = "cashier", "Cajero"
    BARBER = "barber", "Barbero"
    VIEWER = "viewer", "Consultor"


PRIVILEGED_ROLES = frozenset({Role.OWNER, Role.ADMIN})

MODULE_ACTIONS: dict[str, tuple[str, ...]] = {
    "barberia": ("ver", "editar"),
    "usuarios": ("ver", "crear", "editar", "eliminar"),
    "barberos": ("ver", "crear", "editar", "eliminar"),
    "clientes": ("ver", "crear", "editar", "eliminar", "anonimizar"),
    "servicios": ("ver", "crear", "editar", "eliminar"),
    "inventario": ("ver", "crear", "editar", "eliminar", "ajustar"),
    "agenda": ("ver", "crear", "editar", "cancelar"),
    "comandas": ("ver", "crear", "editar", "cerrar", "anular"),
    "caja": ("ver", "abrir", "cerrar", "movimiento"),
    "fiados": ("ver", "crear", "abonar"),
    "alertas": ("ver",),
    "reportes": ("ver", "exportar"),
    "auditoria": ("ver",),
}

ALL_PERMISSIONS = frozenset(f"{module}.{action}" for module, actions in MODULE_ACTIONS.items() for action in actions)

# Igual que en la v1: eliminar catálogo y personal es exclusivo del dueño.
_OWNER_ONLY = frozenset(
    {
        "barberia.editar",
        "usuarios.eliminar",
        "barberos.eliminar",
        "servicios.eliminar",
        "inventario.eliminar",
        "clientes.eliminar",
        "clientes.anonimizar",
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.OWNER: ALL_PERMISSIONS,
    Role.ADMIN: ALL_PERMISSIONS - _OWNER_ONLY,
    Role.CASHIER: frozenset(
        {
            "clientes.ver",
            "clientes.crear",
            "clientes.editar",
            "servicios.ver",
            "inventario.ver",
            "agenda.ver",
            "agenda.crear",
            "agenda.editar",
            "agenda.cancelar",
            "comandas.ver",
            "comandas.crear",
            "comandas.editar",
            "comandas.cerrar",
            "caja.ver",
            "caja.abrir",
            "caja.cerrar",
            "caja.movimiento",
            "fiados.ver",
            "fiados.crear",
            "fiados.abonar",
            "alertas.ver",
            "reportes.ver",
        }
    ),
    # El barbero ve solo lo suyo: además del permiso, los selectores filtran por barbero.
    Role.BARBER: frozenset(
        {
            "clientes.ver",
            "clientes.crear",
            "clientes.editar",
            "servicios.ver",
            "inventario.ver",
            "agenda.ver",
            "agenda.crear",
            "agenda.editar",
            "comandas.ver",
            "comandas.crear",
            "comandas.editar",
            "comandas.cerrar",
        }
    ),
    Role.VIEWER: frozenset(
        {
            "barberos.ver",
            "clientes.ver",
            "servicios.ver",
            "inventario.ver",
            "agenda.ver",
            "comandas.ver",
            "caja.ver",
            "fiados.ver",
            "alertas.ver",
            "reportes.ver",
        }
    ),
}


def role_has_permission(role: str, code: str) -> bool:
    if code not in ALL_PERMISSIONS:
        raise ValueError(f"Permiso desconocido: {code}")
    return code in ROLE_PERMISSIONS.get(role, frozenset())
