"""Escrituras de inventario.

Reglas portadas de MAGNUS v1 (`inventory_service.py`, `category_service.py`,
`service_consumable_service.py`), numeradas como en `docs/migracion-magnus.md`:
30–37 y 40. Defectos corregidos: 14 (bloqueo al tocar stock), 15 (el stock solo
cambia con un movimiento) y 16 (los movimientos son solo-agregar).

Igual que en las demás apps: un objeto inexistente, de otra barbería o borrado
lanza `DoesNotExist`; los datos inválidos, `ValidationError`.

Un módulo por responsabilidad; este paquete reexporta la API pública, así que
`from apps.inventory import services` sigue funcionando igual.
"""

from apps.inventory.services.categories import create_category, soft_delete_category, update_category
from apps.inventory.services.consumables import add_consumable, remove_consumable, update_consumable
from apps.inventory.services.movements import apply_stock_movement, register_adjustment, register_entry
from apps.inventory.services.products import (
    PHOTO_FORMATS,
    PHOTO_MAX_BYTES,
    PHOTO_MAX_PIXELS,
    PHOTO_SIZE,
    ProductData,
    activate_product,
    create_product,
    deactivate_product,
    soft_delete_product,
    update_product,
    upload_product_photo,
)

__all__ = [
    "PHOTO_FORMATS",
    "PHOTO_MAX_BYTES",
    "PHOTO_MAX_PIXELS",
    "PHOTO_SIZE",
    "ProductData",
    "activate_product",
    "add_consumable",
    "apply_stock_movement",
    "create_category",
    "create_product",
    "deactivate_product",
    "register_adjustment",
    "register_entry",
    "remove_consumable",
    "soft_delete_category",
    "soft_delete_product",
    "update_category",
    "update_consumable",
    "update_product",
    "upload_product_photo",
]
