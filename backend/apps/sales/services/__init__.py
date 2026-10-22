"""Escrituras de comandas.

Reglas portadas de MAGNUS v1 (`order_service.py`, `payment_service.py`), numeradas
como en `docs/migracion-magnus.md`: 1–20. Defectos corregidos: 1 (se copia la
comisión al cerrar), 2 (y el costo), 5 (descuento con límites y motivo), 6
(alcance del Barbero), 7 y 8 (precio y tipo siempre del catálogo), 9 (estados),
10 (cierre con bloqueo), 11 (sin saldo huérfano), 12 (anulación con reversos),
13 (sin `str(e)`), 22 (pagos ≤ total). Decisiones 3, 4 y 6.

Igual que en las demás apps: un objeto inexistente, de otra barbería o fuera del
alcance del rol lanza `DoesNotExist`; los datos inválidos, `ValidationError`.

Un módulo por responsabilidad; este paquete reexporta la API pública, así que
`from apps.sales import services` sigue funcionando igual.
"""

from apps.sales.services._shared import NOT_EDITABLE
from apps.sales.services.cancellation import cancel_order
from apps.sales.services.checkout import Checkout, PaymentPart, cash_change, checkout_order
from apps.sales.services.closing import close_order
from apps.sales.services.open_orders import (
    add_item,
    change_order_client,
    create_order,
    hold_order,
    remove_item,
    resume_order,
    set_discount,
    update_item_quantity,
)
from apps.sales.services.quick_charge import quick_register

__all__ = [
    "NOT_EDITABLE",
    "Checkout",
    "PaymentPart",
    "cash_change",
    "change_order_client",
    "checkout_order",
    "add_item",
    "cancel_order",
    "close_order",
    "create_order",
    "hold_order",
    "quick_register",
    "remove_item",
    "resume_order",
    "set_discount",
    "update_item_quantity",
]
