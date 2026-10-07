"""Métodos de pago (decisión 4). Sin modelos, para que tenancy pueda importarlo.

"Combinado" son varios pagos; "cortesía" no es un método sino un descuento del 100 %.
"""

from django.db import models


class PaymentMethod(models.TextChoices):
    CASH = "efectivo", "Efectivo"
    NEQUI = "nequi", "Nequi"
    DAVIPLATA = "daviplata", "Daviplata"
    CARD = "tarjeta", "Tarjeta"
    TRANSFER = "transferencia", "Transferencia"
    BRE_B = "bre_b", "Bre-B"


def all_payment_methods() -> list[str]:
    """Valor por defecto de BarbershopSettings.enabled_payment_methods."""
    return list(PaymentMethod.values)
