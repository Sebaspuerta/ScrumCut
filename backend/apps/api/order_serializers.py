"""Forma de las comandas en la API. Las peticiones solo validan el formato: ningún campo trae un precio ni un
total (salen del catálogo de la sede y del backend); las reglas están en `apps.sales.services`."""

from rest_framework import serializers

from apps.api.fields import MoneyInput, money
from apps.sales.board import OPEN, TABS
from apps.sales.forms import MAX_LINE_QUANTITY
from apps.sales.models import ItemType, OrderStatus
from apps.sales.services.checkout import MAX_PARTS

TOO_MANY_PARTS = f"El pago se divide en {MAX_PARTS} partes como máximo."


class OrderListQuerySerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=TABS, required=False, default=OPEN)
    fecha = serializers.DateField(required=False, allow_null=True, default=None, help_text="AAAA-MM-DD; si falta, hoy.")
    q = serializers.CharField(required=False, max_length=60, default="")
    barbero = serializers.UUIDField(required=False, allow_null=True, default=None)
    page = serializers.IntegerField(required=False, min_value=1, default=1)


class TabSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=TABS)
    label = serializers.CharField()
    count = serializers.IntegerField()


class ClosedSummarySerializer(serializers.Serializer):
    cash = money()
    other = money()
    credit = money()


class OrderRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.IntegerField()
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    client_name = serializers.CharField(help_text="El cliente o «Cliente de mostrador».")
    barbers = serializers.CharField()
    items = serializers.CharField()
    payment = serializers.CharField(help_text="Las formas de pago de la comanda, o «Sin cobro».")
    total = money()
    created_at = serializers.DateTimeField()
    closed_at = serializers.DateTimeField(allow_null=True)
    cancel_reason = serializers.CharField()


class OrderListSerializer(serializers.Serializer):
    tab = serializers.ChoiceField(choices=TABS)
    day = serializers.DateField(help_text="El día de las cerradas y las anuladas.")
    tabs = TabSerializer(many=True)
    summary = ClosedSummarySerializer(allow_null=True, help_text="Solo en las cerradas.")
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField(help_text="Comandas por página.")
    results = OrderRowSerializer(many=True)
    stale_cash = serializers.BooleanField(help_text="La caja de la sede viene de otro día.")


class OrderClientSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    phone = serializers.CharField(allow_null=True, help_text="Enmascarado: 300 *** 4512.")
    level = serializers.CharField(allow_null=True, help_text="Su nivel en las sedes del alcance.")
    visits = serializers.IntegerField()


class OrderLineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=ItemType.choices)
    kind_label = serializers.CharField()
    name = serializers.CharField()
    barber = serializers.CharField(allow_null=True)
    quantity = serializers.IntegerField()
    unit_price = money()
    line_total = money()


class OrderPaymentSerializer(serializers.Serializer):
    method = serializers.CharField()
    amount = money()
    reference = serializers.CharField()


class CreditSerializer(serializers.Serializer):
    debt = money(help_text="Lo que el cliente debe en la sede de la comanda.")
    available = money(allow_null=True, help_text="Su cupo; sin límite en la barbería, null.")


class OrderActionsSerializer(serializers.Serializer):
    edit = serializers.BooleanField()
    discount = serializers.BooleanField()
    checkout = serializers.BooleanField()
    cancel = serializers.BooleanField()


class OrderDetailSerializer(OrderRowSerializer):
    branch = serializers.CharField()
    editable = serializers.BooleanField()
    client = OrderClientSerializer(allow_null=True)
    barber = serializers.CharField(allow_null=True)
    lines = OrderLineSerializer(many=True)
    subtotal = money()
    discount = money()
    discount_reason = serializers.CharField()
    amount_paid = money()
    balance = money()
    payments = OrderPaymentSerializer(many=True)
    credit = CreditSerializer(allow_null=True, help_text="Con cliente registrado; sin cliente no hay fiado.")
    actions = OrderActionsSerializer(help_text="Lo que el rol puede hacer con la comanda en su estado.")


class NamedSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class PricedItemSerializer(NamedSerializer):
    price = money(help_text="El precio vigente en la sede.")


class StockedItemSerializer(PricedItemSerializer):
    stock = serializers.IntegerField(help_text="Existencias en la sede.")


class OptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class OrderCatalogSerializer(serializers.Serializer):
    needs_branch = serializers.BooleanField(help_text="En «todas» no hay precios de sede: hay que elegir una.")
    branch = serializers.CharField(allow_null=True)
    barbers = NamedSerializer(many=True)
    services = PricedItemSerializer(many=True)
    products = StockedItemSerializer(many=True)
    methods = OptionSerializer(many=True, help_text="Las formas de pago habilitadas en la barbería.")
    max_parts = serializers.IntegerField(help_text="Partes máximas de un pago dividido.")
    max_quantity = serializers.IntegerField(help_text="Unidades máximas por línea.")


class ClientSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, max_length=60, default="")


class ClientChoiceSerializer(NamedSerializer):
    phone = serializers.CharField(allow_null=True)


class NewLineSerializer(serializers.Serializer):
    """Un servicio o un producto (el service exige uno de los dos), sin precio."""

    service = serializers.UUIDField(required=False, allow_null=True, default=None)
    product = serializers.UUIDField(required=False, allow_null=True, default=None)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_LINE_QUANTITY, default=1)
    barber = serializers.UUIDField(required=False, allow_null=True, default=None)


class NewOrderSerializer(serializers.Serializer):
    client = serializers.UUIDField(required=False, allow_null=True, default=None)
    barber = serializers.UUIDField(required=False, allow_null=True, default=None)
    lines = NewLineSerializer(many=True, required=False, default=list)


class ChangeClientSerializer(serializers.Serializer):
    client = serializers.UUIDField(allow_null=True, help_text="null la deja como cliente de mostrador.")


class DiscountSerializer(serializers.Serializer):
    amount = MoneyInput()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")


class PaymentPartSerializer(serializers.Serializer):
    method = serializers.CharField(max_length=20, help_text="Una forma de pago habilitada o «fiado».")
    amount = MoneyInput(required=False, allow_null=True, default=None, help_text="Sin monto, todo el total.")
    reference = serializers.CharField(required=False, allow_blank=True, max_length=80, default="")


class CheckoutSerializer(serializers.Serializer):
    parts = PaymentPartSerializer(
        many=True, min_length=1, max_length=MAX_PARTS, error_messages={"max_length": TOO_MANY_PARTS}
    )
    received = MoneyInput(required=False, allow_null=True, default=None, help_text="El efectivo entregado.")
    due_date = serializers.DateField(required=False, allow_null=True, default=None, help_text="Fecha del fiado.")


class CheckoutResultSerializer(serializers.Serializer):
    order = OrderDetailSerializer()
    change = money(help_text="Las vueltas, solo sobre la parte en efectivo.")


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300)
