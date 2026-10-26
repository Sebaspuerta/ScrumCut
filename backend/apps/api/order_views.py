"""API de Comandas (fase R2). Vistas delgadas: validan el formato y llaman a los services de `apps.sales`,
los mismos de las pantallas de Django, con el alcance de sede de la petición.

Escribir exige una sede (`branch_for_write` en cada service): en "todas" responde 400 con el mensaje que
pide elegirla. Un objeto de otra sede, de otro barbero o de otra barbería no se encuentra (404).
"""

from uuid import UUID

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.order_serializers import (
    CancelSerializer,
    ChangeClientSerializer,
    CheckoutResultSerializer,
    CheckoutSerializer,
    ClientChoiceSerializer,
    ClientSearchQuerySerializer,
    DiscountSerializer,
    NewLineSerializer,
    NewOrderSerializer,
    OrderCatalogSerializer,
    OrderDetailSerializer,
    OrderListQuerySerializer,
    OrderListSerializer,
)
from apps.api.orders import client_choice, order_catalog, order_detail, order_list
from apps.api.permissions import HasRolePermission
from apps.api.serializers import OBJECT_READ_ERRORS, OBJECT_WRITE_ERRORS, READ_ERRORS, WRITE_ERRORS
from apps.cash.selectors import payment_methods
from apps.clients.selectors import list_clients
from apps.sales import services
from apps.sales.board import BoardFilter
from apps.sales.forms import CheckoutForm
from apps.sales.services.checkout import MAX_PARTS

CLIENT_RESULTS = 20  # como el buscador de "Cambiar cliente" en Django
PART_FIELDS = ("metodo", "monto", "referencia")
CHECKOUT_FORM_FIELDS = {"metodo": "parts", "referencia": "parts", "recibido": "received", "vence": "due_date"} | {
    f"parte_{number}_{field}": "parts" for number in range(1, MAX_PARTS + 1) for field in PART_FIELDS
}


class OrderWriteView(APIView):
    """Cada escritura responde la comanda como queda, leída de nuevo por el alcance. `error_fields` traduce las
    claves de los errores de los services a los campos de la API (`apps.api.exceptions`)."""

    error_fields: dict[str, str] = {}

    permission_classes = [IsAuthenticated, HasRolePermission]

    def valid(self, serializer_class: type[serializers.Serializer]) -> dict:
        body = serializer_class(data=self.request.data)
        body.is_valid(raise_exception=True)
        return body.validated_data

    def order(self, public_id: UUID, status_code: int = status.HTTP_200_OK) -> Response:
        data = order_detail(self.request.membership, public_id, scope=self.request.branch_scope)
        return Response(OrderDetailSerializer(data).data, status=status_code)


class OrderCreateView(OrderWriteView):
    """Abre la comanda en la sede del alcance con sus líneas, al precio vigente de la sede."""

    required_permission = "comandas.crear"
    error_fields = {"client": "client", "barber": "barber", "service": "lines", "product": "lines", "quantity": "lines"}

    @extend_schema(request=NewOrderSerializer, responses={201: OrderDetailSerializer, **WRITE_ERRORS})
    def post(self, request: Request) -> Response:
        data = self.valid(NewOrderSerializer)
        lines = [services.NewLine(**line) for line in data["lines"]]
        order = services.open_order_with_lines(
            request.membership, request.branch_scope, client=data["client"], barber=data["barber"], lines=lines
        )
        return self.order(order.public_id, status.HTTP_201_CREATED)


class OrderClientView(OrderWriteView):
    required_permission = "comandas.editar"
    error_fields = {"client": "client"}

    @extend_schema(request=ChangeClientSerializer, responses={200: OrderDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(ChangeClientSerializer)
        services.change_order_client(request.membership, public_id, scope=request.branch_scope, client=data["client"])
        return self.order(public_id)


class OrderLinesView(OrderWriteView):
    """El precio no viaja: `add_item` lo toma del catálogo de la sede de la comanda."""

    required_permission = "comandas.editar"
    error_fields = {"service": "service", "product": "product", "quantity": "quantity", "barber": "barber"}

    @extend_schema(request=NewLineSerializer, responses={200: OrderDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(NewLineSerializer)
        services.add_item(request.membership, public_id, scope=request.branch_scope, **data)
        return self.order(public_id)


class OrderLineRemoveView(OrderWriteView):
    required_permission = "comandas.editar"

    @extend_schema(request=None, responses={200: OrderDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID, item: UUID) -> Response:
        services.remove_item(request.membership, public_id, scope=request.branch_scope, item=item)
        return self.order(public_id)


class OrderDiscountView(OrderWriteView):
    required_permission = "comandas.descontar"
    error_fields = {"discount": "amount", "discount_reason": "reason"}

    @extend_schema(request=DiscountSerializer, responses={200: OrderDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(DiscountSerializer)
        services.set_discount(
            request.membership, public_id, scope=request.branch_scope, amount=data["amount"], reason=data["reason"]
        )
        return self.order(public_id)


def _checkout_form(data: dict) -> CheckoutForm:
    """El mismo formulario de la pantalla de Django: valida las formas de pago habilitadas, las partes y que
    con efectivo se indique lo recibido. Sin montos es una sola forma de pago por el total."""
    parts, first = data["parts"], data["parts"][0]
    fields = {"metodo": first["method"], "referencia": first["reference"]}
    fields |= {"recibido": data["received"] or "", "vence": data["due_date"] or ""}
    if len(parts) > 1 or first["amount"] is not None:
        for number, part in enumerate(parts, start=1):
            fields[f"parte_{number}_metodo"] = part["method"]
            fields[f"parte_{number}_monto"] = "" if part["amount"] is None else part["amount"]
            fields[f"parte_{number}_referencia"] = part["reference"]
    form = CheckoutForm(fields, methods=payment_methods())
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    return form


class OrderCheckoutView(OrderWriteView):
    """Un solo cobro aunque llegue dos veces: `close_order` bloquea la comanda y la segunda la encuentra cerrada."""

    required_permission = "comandas.cerrar"
    error_fields = CHECKOUT_FORM_FIELDS | {"payments": "parts"}

    @extend_schema(request=CheckoutSerializer, responses={200: CheckoutResultSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        checkout = _checkout_form(self.valid(CheckoutSerializer)).checkout()
        order, change = services.checkout_order(
            request.membership, public_id, scope=request.branch_scope, checkout=checkout
        )
        detail = order_detail(request.membership, order.public_id, scope=request.branch_scope)
        return Response(CheckoutResultSerializer({"order": detail, "change": change}).data)


class OrderCancelView(OrderWriteView):
    """`cancel_order` exige comandas.editar si está abierta y comandas.anular si ya se cerró."""

    required_permission = "comandas.ver"
    error_fields = {"reason": "reason"}

    @extend_schema(request=CancelSerializer, responses={200: OrderDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(CancelSerializer)
        services.cancel_order(request.membership, public_id, scope=request.branch_scope, reason=data["reason"])
        return self.order(public_id)


def _list_query(request: Request) -> dict:
    query = OrderListQuerySerializer(data=request.query_params)
    if query.is_valid():
        return query.validated_data
    defaults = OrderListQuerySerializer(data={})
    defaults.is_valid(raise_exception=True)
    return defaults.validated_data


class OrderListView(APIView):
    """La lista por pestaña (?estado=abiertas|cerradas|anuladas) y día (?fecha=); un valor inválido vuelve al
    valor por defecto, como en la pantalla de Django."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "comandas.ver"

    @extend_schema(
        operation_id="orders_list",
        parameters=[OrderListQuerySerializer],
        responses={200: OrderListSerializer, **READ_ERRORS},
    )
    def get(self, request: Request) -> Response:
        data = _list_query(request)
        filters = BoardFilter(tab=data["estado"], search=data["q"], barber=data["barbero"], day=data["fecha"])
        page = order_list(request.membership, scope=request.branch_scope, filters=filters, page=data["page"])
        return Response(OrderListSerializer(page).data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "comandas.ver"

    @extend_schema(responses={200: OrderDetailSerializer, **OBJECT_READ_ERRORS})
    def get(self, request: Request, public_id: UUID) -> Response:
        data = order_detail(request.membership, public_id, scope=request.branch_scope)
        return Response(OrderDetailSerializer(data).data)


class OrderCatalogView(APIView):
    """Barberos, servicios y productos con su precio y stock en la sede, y las formas de pago habilitadas."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "comandas.ver"

    @extend_schema(responses={200: OrderCatalogSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        data = order_catalog(request.membership, scope=request.branch_scope)
        return Response(OrderCatalogSerializer(data).data)


class ClientSearchView(APIView):
    """Cualquier cliente de la barbería por nombre, celular o documento; solo su nombre y el celular enmascarado."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "clientes.ver"

    @extend_schema(
        parameters=[ClientSearchQuerySerializer], responses={200: ClientChoiceSerializer(many=True), **READ_ERRORS}
    )
    def get(self, request: Request) -> Response:
        query = ClientSearchQuerySerializer(data=request.query_params)
        term = query.validated_data["q"].strip() if query.is_valid() else ""
        clients = list_clients(request.membership, term)[:CLIENT_RESULTS] if term else []
        return Response(ClientChoiceSerializer([client_choice(client) for client in clients], many=True).data)
