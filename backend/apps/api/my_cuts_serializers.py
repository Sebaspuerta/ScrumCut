"""Forma de «Mis cortes» en la API. El dinero viaja como texto decimal."""

from rest_framework import serializers

from apps.api.fields import money


class MyCutsQuerySerializer(serializers.Serializer):
    """Solo el día y la página: el barbero sale de la sesión, así que no hay parámetro para elegirlo."""

    fecha = serializers.DateField(required=False, allow_null=True, default=None, help_text="AAAA-MM-DD; si falta, hoy.")
    page = serializers.IntegerField(required=False, min_value=1, default=1)


class ProductionSerializer(serializers.Serializer):
    orders = serializers.IntegerField(help_text="Comandas cerradas en las que hizo alguna línea.")
    cuts = serializers.IntegerField(help_text="Servicios hechos.")
    production = money(help_text="La venta neta de sus líneas.")
    commission = money(help_text="La comisión que quedó en cada comanda al cerrarla.")


class MyOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.IntegerField()
    closed_at = serializers.DateTimeField()
    items = serializers.CharField(help_text="Sus líneas en la comanda.")
    cuts = serializers.IntegerField()
    production = money()
    commission = money()


class MyCutsSerializer(serializers.Serializer):
    barber = serializers.CharField(allow_null=True, help_text="El barbero de la sesión; sin uno propio, null.")
    day = serializers.DateField(help_text="El día de la lista.")
    today = ProductionSerializer()
    month = ProductionSerializer(help_text="Del primer día del mes hasta hoy.")
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField(help_text="Comandas por página.")
    results = MyOrderSerializer(many=True)
