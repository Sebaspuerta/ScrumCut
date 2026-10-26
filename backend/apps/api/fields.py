"""Campos de dinero de la API: viaja como texto decimal (o entero de pesos al entrar), nunca como float."""

from decimal import Decimal

from rest_framework import serializers

MONEY = {"max_digits": 14, "decimal_places": 2}


def money(**kwargs) -> serializers.DecimalField:
    """Dinero en las respuestas: texto decimal ("25000.00"); lo formatea el cliente."""
    return serializers.DecimalField(**MONEY, **kwargs)


class MoneyInput(serializers.DecimalField):
    """Dinero en las peticiones: "25000", "25000.00" o 25000. Un número con decimales de JSON llega como
    float y se rechaza: el monto nunca pasa por un float."""

    default_error_messages = {"float": "Envía el monto como texto o como un entero de pesos."}

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("min_value", Decimal("0"))
        super().__init__(**MONEY, **kwargs)

    def to_internal_value(self, data) -> Decimal:
        if isinstance(data, float):
            self.fail("float")
        return super().to_internal_value(data)
