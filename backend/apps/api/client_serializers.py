"""Forma de los clientes en la API. Las peticiones solo validan el formato con los mismos topes del formulario de
Django; el celular colombiano, los duplicados, la autorización de datos y la auditoría están en `apps.clients`."""

from rest_framework import serializers

from apps.api.fields import money
from apps.api.order_serializers import OptionSerializer
from apps.api.receivable_serializers import ReceivableRowSerializer
from apps.clients.forms import ORDER_LABELS, ClientForm
from apps.clients.models import Client
from apps.clients.selectors import ClientStatus

_FORM = ClientForm.base_fields
# El formulario de Django no limita el correo: el tope es el de la columna.
EMAIL_MAX_LENGTH = Client._meta.get_field("email").max_length


class ClientListQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, max_length=60, default="", help_text="Nombre, celular o cédula.")
    nivel = serializers.ChoiceField(choices=ClientStatus.choices, required=False, allow_blank=True, default="")
    orden = serializers.ChoiceField(choices=ORDER_LABELS, required=False, default=ORDER_LABELS[0][0])
    page = serializers.IntegerField(required=False, min_value=1, default=1)


class LevelCountSerializer(serializers.Serializer):
    value = serializers.CharField(help_text="Un nivel, o vacío para «Todos».")
    label = serializers.CharField()
    count = serializers.IntegerField()


class ClientStatsSerializer(serializers.Serializer):
    active = serializers.IntegerField(help_text="Con visitas en los últimos 90 días.")
    with_visits = serializers.IntegerField()
    new_this_month = serializers.IntegerField()
    new_last_month = serializers.IntegerField()
    return_rate = serializers.IntegerField(allow_null=True, help_text="Vuelven en 30 días, en %; sin cohorte, null.")
    debtors = serializers.IntegerField(help_text="Clientes con fiado.")
    debt_total = money()


class ClientRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    phone = serializers.CharField(allow_null=True, help_text="Enmascarado: 300 *** 4512.")
    has_activity = serializers.BooleanField(help_text="Sin actividad en la sede: encontrado por búsqueda, sin cifras.")
    level = serializers.ChoiceField(choices=ClientStatus.choices, allow_null=True)
    level_label = serializers.CharField(help_text="El nivel, «Varía por sede» en «todas» o «Sin visitas en la sede».")
    visits = serializers.IntegerField(allow_null=True)
    last_visit = serializers.DateTimeField(allow_null=True)
    spent_recent = money(allow_null=True, help_text="Gasto de los últimos 90 días.")
    debt = money(allow_null=True)


class DataPolicySerializer(serializers.Serializer):
    version = serializers.CharField()
    url = serializers.CharField(help_text="El texto vigente, para leerlo con el cliente.")


class ClientListSerializer(serializers.Serializer):
    search = serializers.CharField()
    level = serializers.CharField()
    order = serializers.CharField()
    levels = LevelCountSerializer(many=True, help_text="Los filtros por nivel con su conteo.")
    orderings = OptionSerializer(many=True)
    stats = ClientStatsSerializer()
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField(help_text="Clientes por página.")
    results = ClientRowSerializer(many=True)
    data_policy = DataPolicySerializer(
        allow_null=True, help_text="Sin una política publicada no se registran clientes."
    )


class LevelProgressSerializer(serializers.Serializer):
    next = serializers.CharField(allow_null=True, help_text="El siguiente nivel por visitas; en el más alto, null.")
    missing = serializers.IntegerField()
    percent = serializers.IntegerField()


class FavoriteBarberSerializer(serializers.Serializer):
    name = serializers.CharField()
    visits = serializers.IntegerField()


class ClientVisitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    closed_at = serializers.DateTimeField()
    items = serializers.CharField()
    barber = serializers.CharField(allow_null=True)
    methods = serializers.CharField(help_text="Las formas de pago, o «Fiado».")
    total = money()


class ClientActivitySerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=ClientStatus.choices, allow_null=True)
    level_label = serializers.CharField()
    progress = LevelProgressSerializer()
    visits = serializers.IntegerField()
    spent = money()
    ticket = money()
    barber = FavoriteBarberSerializer(allow_null=True)
    favorite = serializers.CharField(allow_null=True, help_text="El servicio que más pide.")
    balance = money(help_text="Lo que debe en las sedes del alcance.")
    open_debt = serializers.UUIDField(allow_null=True, help_text="Su fiado vivo más antiguo, para abonarlo.")
    last_visits = ClientVisitSerializer(many=True)


class ClientActionsSerializer(serializers.Serializer):
    edit = serializers.BooleanField()
    new_order = serializers.BooleanField(help_text="Con comandas.crear y una sede elegida.")


class ClientDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    initials = serializers.CharField()
    phone = serializers.CharField(allow_null=True, help_text="Enmascarado: 300 *** 4512.")
    email = serializers.CharField(allow_null=True, help_text="Solo con clientes.editar, para el formulario.")
    notes = serializers.CharField(help_text="Preferencias y notas.")
    since = serializers.DateTimeField(help_text="Cliente desde.")
    activity = ClientActivitySerializer(allow_null=True, help_text="Sin historial en la sede, null.")
    receivables = ReceivableRowSerializer(
        many=True, allow_null=True, help_text="Sus fiados aquí; sin fiados.ver, null."
    )
    actions = ClientActionsSerializer()


class ClientUpdateSerializer(serializers.Serializer):
    """Celular y cédula vacíos no cambian: no se muestran al editar."""

    full_name = serializers.CharField(max_length=_FORM["full_name"].max_length)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=_FORM["phone"].max_length, default="")
    document = serializers.CharField(
        required=False, allow_blank=True, max_length=_FORM["document"].max_length, default=""
    )
    email = serializers.CharField(
        required=False, allow_blank=True, max_length=EMAIL_MAX_LENGTH, default="", help_text="Lo valida ClientForm."
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=_FORM["notes"].max_length, default="")


class ClientSerializer(ClientUpdateSerializer):
    consent = serializers.BooleanField(default=False, help_text="El cliente autoriza la política de datos vigente.")
    other_person = serializers.BooleanField(default=False, help_text="Es otra persona con el mismo nombre.")
