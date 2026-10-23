"""Forma de la respuesta del tablero. El dinero viaja como texto decimal (nunca float) y lo formatea el cliente."""

from rest_framework import serializers

from apps.api.serializers import AlertItemSerializer


def money(**kwargs) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=14, decimal_places=2, **kwargs)


class VariationSerializer(serializers.Serializer):
    percent = serializers.DecimalField(max_digits=8, decimal_places=1)
    direction = serializers.ChoiceField(choices=["up", "down"])


class IncomeKpiSerializer(serializers.Serializer):
    value = money()
    variation = VariationSerializer(allow_null=True)


class OrdersKpiSerializer(serializers.Serializer):
    value = serializers.IntegerField()
    open = serializers.IntegerField()
    variation = VariationSerializer(allow_null=True)


class TicketKpiSerializer(serializers.Serializer):
    value = money(allow_null=True)
    variation = VariationSerializer(allow_null=True)


class CashKpiSerializer(serializers.Serializer):
    expected = money()
    opened_at = serializers.DateTimeField()


class ReceivablesKpiSerializer(serializers.Serializer):
    pending_count = serializers.IntegerField()
    pending_balance = money()
    overdue_count = serializers.IntegerField()
    overdue_balance = money()
    clients = serializers.IntegerField()


class KpisSerializer(serializers.Serializer):
    comparison = serializers.CharField(help_text="Contra qué se comparan los de hoy.")
    income = IncomeKpiSerializer()
    orders = OrdersKpiSerializer()
    ticket = TicketKpiSerializer()
    cash = CashKpiSerializer(allow_null=True, help_text="Sin cajas abiertas en el alcance, null.")
    receivables = ReceivablesKpiSerializer()


class TrendSerializer(serializers.Serializer):
    income = serializers.ListField(child=money())
    orders = serializers.ListField(child=serializers.IntegerField())
    ticket = serializers.ListField(child=money())


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    day = serializers.IntegerField()
    total = money()
    level = serializers.IntegerField(help_text="0 a 4, frente al mejor día del mes.")
    ratio = serializers.FloatField(help_text="Proporción frente al mejor día: alto de la torre, no dinero.")
    today = serializers.BooleanField()
    future = serializers.BooleanField()
    has_sales = serializers.BooleanField()
    orders = serializers.IntegerField()
    ticket = money(allow_null=True)


class CalendarWeekSerializer(serializers.Serializer):
    days = CalendarDaySerializer(many=True, help_text="Los días del mes en esa semana, de lunes a domingo.")
    total = money()


class DayTotalSerializer(serializers.Serializer):
    date = serializers.DateField()
    total = money()


class CalendarSerializer(serializers.Serializer):
    weeks = CalendarWeekSerializer(many=True)
    total = money()
    selling_days = serializers.IntegerField()
    daily_average = money(allow_null=True)
    best = DayTotalSerializer(allow_null=True)
    last_sale = DayTotalSerializer(allow_null=True)


class CashStepSerializer(serializers.Serializer):
    label = serializers.CharField()
    kind = serializers.ChoiceField(choices=["total", "up", "down", "counted"])
    amount = money()


class CashFlowSerializer(serializers.Serializer):
    is_open = serializers.BooleanField()
    opened_at = serializers.DateTimeField()
    expected = money()
    difference = money(allow_null=True)
    steps = CashStepSerializer(many=True)


class DashboardCashSerializer(serializers.Serializer):
    needs_branch = serializers.BooleanField(help_text="En «todas» no se mezclan cajas: hay que elegir una sede.")
    flow = CashFlowSerializer(allow_null=True)


class BarberRowSerializer(serializers.Serializer):
    name = serializers.CharField()
    orders = serializers.IntegerField()
    services = serializers.IntegerField()
    sales = money()
    commission = money()


class ProductRowSerializer(serializers.Serializer):
    name = serializers.CharField()
    units = serializers.IntegerField()
    sales = money()
    margin = serializers.DecimalField(max_digits=6, decimal_places=0, allow_null=True)


class ClosingRowSerializer(serializers.Serializer):
    date = serializers.DateField()
    expected = money()
    counted = money()
    difference = money()


class DashboardSerializer(serializers.Serializer):
    month = serializers.CharField(help_text="AAAA-MM.")
    month_label = serializers.CharField()
    previous_month = serializers.CharField(allow_null=True)
    next_month = serializers.CharField(allow_null=True)
    today = serializers.DateField()
    timezone = serializers.CharField()
    scope_label = serializers.CharField()
    stale_cash = serializers.BooleanField(help_text="La caja de la sede viene de otro día.")
    kpis = KpisSerializer()
    trend = TrendSerializer()
    calendar = CalendarSerializer()
    cash = DashboardCashSerializer()
    unread_alerts = serializers.IntegerField(allow_null=True)
    barbers = BarberRowSerializer(many=True)
    products = ProductRowSerializer(many=True)
    closings = ClosingRowSerializer(many=True)
    alerts = AlertItemSerializer(many=True)


class DashboardQuerySerializer(serializers.Serializer):
    mes = serializers.CharField(required=False, max_length=7, help_text="AAAA-MM; si no vale, el mes actual.")
