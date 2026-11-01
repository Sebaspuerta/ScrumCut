"""Forma de los fiados en la API. El abono trae el monto, la forma de pago, el saldo que vio quien abona y, opcionales,
la referencia y la nota; que no pase el saldo y vaya a la caja de la sede de origen lo decide `add_payment`."""

from decimal import Decimal

from rest_framework import serializers

from apps.api.fields import MoneyInput, money
from apps.api.order_serializers import NamedSerializer, OptionSerializer
from apps.cash.choices import PAYMENT_REFERENCE_MAX_LENGTH
from apps.receivables.board import PENDING
from apps.receivables.forms import TABS, PaymentForm
from apps.receivables.models import ReceivableStatus


class ReceivableListQuerySerializer(serializers.Serializer):
    pestana = serializers.ChoiceField(choices=TABS, required=False, default=PENDING)
    q = serializers.CharField(required=False, max_length=60, default="", help_text="El nombre del cliente.")
    page = serializers.IntegerField(required=False, min_value=1, default=1)


class ReceivableOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.IntegerField()


class ReceivableRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    client = NamedSerializer()
    order = ReceivableOrderSerializer(allow_null=True, help_text="Sin comanda, es un fiado manual.")
    branch = serializers.CharField(help_text="La sede de origen: solo ahí se abona.")
    created_at = serializers.DateTimeField()
    due_date = serializers.DateField(allow_null=True)
    total = money()
    paid = money(help_text="Lo abonado: total − saldo.")
    balance = money()
    status = serializers.ChoiceField(choices=ReceivableStatus.choices)
    due_text = serializers.CharField(help_text="«▾ Vencido hace 3 días», «Vence en 2 días», «Al día», «Pagado»…")
    due_tone = serializers.CharField(help_text="overdue, soon, ok o done: el estado sin rojos.")


class ReceivableTabSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=TABS)
    label = serializers.CharField()
    count = serializers.IntegerField()


class DebtFigureSerializer(serializers.Serializer):
    total = money()
    clients = serializers.IntegerField()


class PendingFigureSerializer(DebtFigureSerializer):
    count = serializers.IntegerField(help_text="Fiados con saldo.")


class OverdueFigureSerializer(DebtFigureSerializer):
    share = serializers.IntegerField(allow_null=True, help_text="Porcentaje de la cartera; sin cartera, null.")


class CollectedFigureSerializer(serializers.Serializer):
    total = money()
    count = serializers.IntegerField(help_text="Abonos del mes.")


class PortfolioSerializer(serializers.Serializer):
    pending = PendingFigureSerializer(help_text="Por cobrar.")
    overdue = OverdueFigureSerializer()
    due_soon = DebtFigureSerializer(help_text="Vence en los próximos 7 días.")
    collected = CollectedFigureSerializer(help_text="Cobrado en el mes.")


class AgingSerializer(serializers.Serializer):
    key = serializers.CharField(help_text="current, d1_15, d16_30 o d30: del más nuevo al más viejo.")
    label = serializers.CharField()
    amount = money()
    percent = serializers.IntegerField(help_text="Su parte del total por cobrar.")


class ReceivableListSerializer(serializers.Serializer):
    today = serializers.DateField(help_text="Hoy en la zona de la barbería: el mes de lo cobrado.")
    tab = serializers.ChoiceField(choices=TABS)
    tabs = ReceivableTabSerializer(many=True)
    portfolio = PortfolioSerializer()
    aging = AgingSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField(help_text="Fiados por página.")
    results = ReceivableRowSerializer(many=True, help_text="Los vivos por urgencia; los pagados, los más recientes.")


class PaymentEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    at = serializers.DateTimeField()
    method = serializers.CharField()
    reference = serializers.CharField()
    amount = money()
    received_by = serializers.CharField()


class ReceivableActionsSerializer(serializers.Serializer):
    pay = serializers.BooleanField(help_text="Con fiados.abonar, saldo vivo y una sede elegida.")


class ReceivableDetailSerializer(ReceivableRowSerializer):
    notes = serializers.CharField()
    payments = PaymentEntrySerializer(many=True, help_text="Los abonos, el más reciente primero.")
    methods = OptionSerializer(many=True, help_text="Las formas de pago habilitadas en la barbería.")
    actions = ReceivableActionsSerializer()
    needs_branch = serializers.BooleanField(help_text="En «todas»: para abonar hay que elegir la sede de origen.")


class ReceivablePaymentSerializer(serializers.Serializer):
    amount = MoneyInput(min_value=Decimal("0.01"))
    method = serializers.CharField(max_length=20, help_text="Una forma de pago habilitada.")
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=PAYMENT_REFERENCE_MAX_LENGTH,
        default="",
        help_text="Nequi 4821: solo con los medios que no son efectivo.",
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=PaymentForm.base_fields["nota"].max_length,
        default="",
        help_text="Nota libre: queda en la descripción del movimiento de caja.",
    )
    expected_balance = MoneyInput(
        help_text="El saldo que vio quien abona: un segundo envío del mismo abono se rechaza."
    )
