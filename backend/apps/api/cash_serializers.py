"""Forma de la caja en la API. El contado no viaja: se envía cuántos billetes hay de cada denominación y las
monedas, y el servidor suma (`CloseSessionForm.counted`)."""

from decimal import Decimal

from rest_framework import serializers

from apps.api.fields import MoneyInput, money
from apps.api.order_serializers import OptionSerializer
from apps.cash.forms import BILLS, MOVEMENT_FILTERS
from apps.cash.models import Direction, MovementKind

MANUAL_CHOICES = [MovementKind.MANUAL_INCOME, MovementKind.EXPENSE, MovementKind.WITHDRAWAL]
MAX_BILLS = 100000  # el mismo tope por denominación del formulario de Django
UNKNOWN_BILL = "Esa denominación no es un billete en circulación."


class CashQuerySerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=MOVEMENT_FILTERS, required=False, default="")


class KindTotalSerializer(serializers.Serializer):
    total = money()
    count = serializers.IntegerField()


class CashStripSerializer(serializers.Serializer):
    sales = KindTotalSerializer(help_text="Ventas en efectivo.")
    receivable_payments = KindTotalSerializer(help_text="Abonos de fiados en efectivo.")
    expenses = KindTotalSerializer()
    withdrawals = KindTotalSerializer()


class CashMovementSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    at = serializers.DateTimeField()
    kind = serializers.ChoiceField(choices=MovementKind.choices)
    kind_label = serializers.CharField()
    description = serializers.CharField()
    by = serializers.CharField()
    direction = serializers.ChoiceField(choices=Direction.choices)
    amount = money()


class OtherMediaSerializer(serializers.Serializer):
    transfers = KindTotalSerializer(help_text="Ventas por otros medios: no entran a la caja física.")
    credit = KindTotalSerializer(help_text="Fiados nuevos de hoy en la sede.")


class CashSessionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    opened_at = serializers.DateTimeField()
    opened_by = serializers.CharField()
    stale = serializers.BooleanField(help_text="Viene de otro día: no recibe efectivo y solo se cierra.")
    opening_amount = money()
    strip = CashStripSerializer()
    expected = money(help_text="Base + entradas en efectivo − salidas en efectivo.")
    movements = CashMovementSerializer(many=True, help_text="Lo que entra o sale de la caja física.")
    other_media = OtherMediaSerializer()


class CashActionsSerializer(serializers.Serializer):
    open = serializers.BooleanField()
    movement = serializers.BooleanField()
    close = serializers.BooleanField()


class CashStateSerializer(serializers.Serializer):
    needs_branch = serializers.BooleanField(help_text="En «todas» no se mezclan cajas: hay que elegir una sede.")
    branch = serializers.CharField(allow_null=True)
    today = serializers.DateField()
    kind = serializers.CharField(help_text="El filtro de movimientos aplicado; vacío, todos.")
    kinds = OptionSerializer(many=True, help_text="Los filtros de movimientos.")
    manual_kinds = OptionSerializer(many=True, help_text="Lo que se registra a mano, siempre en efectivo.")
    denominations = serializers.ListField(child=serializers.IntegerField(), help_text="Billetes, del mayor al menor.")
    session = CashSessionSerializer(allow_null=True)
    actions = CashActionsSerializer()


class OpenCashSerializer(serializers.Serializer):
    opening_amount = MoneyInput()


class ManualMovementSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=MANUAL_CHOICES)
    amount = MoneyInput(min_value=Decimal("0.01"))
    description = serializers.CharField(max_length=200)


class BillCountSerializer(serializers.Serializer):
    denomination = serializers.IntegerField(help_text="Una de `denominations` de la caja.")
    count = serializers.IntegerField(min_value=0, max_value=MAX_BILLS)

    def validate_denomination(self, value: int) -> int:
        if value not in BILLS:
            raise serializers.ValidationError(UNKNOWN_BILL)
        return value


class CloseCashSerializer(serializers.Serializer):
    bills = BillCountSerializer(many=True)
    coins = MoneyInput(help_text="Las monedas, como un total en pesos.")
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")


class ClosingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    branch = serializers.CharField()
    closed_at = serializers.DateTimeField()
    closed_by = serializers.CharField()
    expected = money()
    counted = money()
    difference = money(help_text="Contado − esperado: positivo sobra, negativo falta.")
    notes = serializers.CharField()


class ClosingsQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)


class ClosingsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField(help_text="Cierres por página.")
    results = ClosingSerializer(many=True)
