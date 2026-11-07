"""API de las existencias (fase R7): entrada, ajuste y traslado, el precio por sede y los avisos de stock.

Todo sale de la sede del alcance y pasa por los services de `apps.inventory`: en «todas» responde 400 con el mensaje
que pide elegir una sede. Cada movimiento lleva la llave del intento (`request_key`): un reenvío con la misma llave
responde 200 con lo ya registrado, sin mover el stock otra vez; la misma llave con otros datos, 409.
"""

from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.exceptions import Conflict
from apps.api.inventory import stock_alerts
from apps.api.inventory_serializers import (
    AdjustmentSerializer,
    BranchPriceSerializer,
    EntrySerializer,
    ProductDetailSerializer,
    StockAlertsSerializer,
    TransferSerializer,
)
from apps.api.inventory_views import InventoryWriteView
from apps.api.permissions import HasRolePermission
from apps.api.serializers import OBJECT_WRITE_ERRORS, READ_ERRORS, error_responses
from apps.inventory import services

STOCK_ERRORS = {**OBJECT_WRITE_ERRORS, **error_responses(409)}
STOCK_FIELDS = {"quantity": "quantity", "reason": "reason", "unit_cost": "unit_cost", "destination": "destination"}


class StockWriteView(InventoryWriteView):
    """201 si se registró ahora; 200 si la llave ya estaba registrada con los mismos datos."""

    required_permission = "inventario.ajustar"
    error_fields = STOCK_FIELDS

    def registered(self, public_id: UUID, *, now: bool) -> Response:
        return self.product(public_id, status.HTTP_201_CREATED if now else status.HTTP_200_OK)


class EntryView(StockWriteView):
    """Regla 33: cantidad mayor que cero, costo unitario (sin él, el del producto) y motivo."""

    @extend_schema(
        request=EntrySerializer, responses={201: ProductDetailSerializer, 200: ProductDetailSerializer, **STOCK_ERRORS}
    )
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(EntrySerializer)
        try:
            _, now = services.register_entry_once(request.membership, public_id, scope=request.branch_scope, **data)
        except services.StockRequestConflictError as exc:
            raise Conflict from exc
        return self.registered(public_id, now=now)


class AdjustmentView(StockWriteView):
    """Regla 34: con signo y motivo obligatorio; nunca deja la existencia negativa."""

    @extend_schema(
        request=AdjustmentSerializer,
        responses={201: ProductDetailSerializer, 200: ProductDetailSerializer, **STOCK_ERRORS},
    )
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(AdjustmentSerializer)
        try:
            _, now = services.register_adjustment_once(
                request.membership, public_id, scope=request.branch_scope, **data
            )
        except services.StockRequestConflictError as exc:
            raise Conflict from exc
        return self.registered(public_id, now=now)


class TransferView(StockWriteView):
    """Sale de la sede del alcance y entra en otra sede activa de la barbería, en una sola transacción."""

    @extend_schema(
        request=TransferSerializer,
        responses={201: ProductDetailSerializer, 200: ProductDetailSerializer, **STOCK_ERRORS},
    )
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(TransferSerializer)
        try:
            _, now = services.transfer_stock_once(request.membership, public_id, scope=request.branch_scope, **data)
        except services.StockRequestConflictError as exc:
            raise Conflict from exc
        return self.registered(public_id, now=now)


class BranchPriceView(InventoryWriteView):
    """Decisión 17: el precio de venta propio de la sede del alcance; sin él, rige el del catálogo."""

    required_permission = "inventario.editar"
    error_fields = {"price": "price"}

    @extend_schema(request=BranchPriceSerializer, responses={200: ProductDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        price = self.valid(BranchPriceSerializer)["price"]
        services.set_product_branch_price(request.membership, public_id, scope=request.branch_scope, price=price)
        return self.product(public_id)


class BranchPriceRemoveView(InventoryWriteView):
    required_permission = "inventario.editar"
    error_fields = {"price": "price"}

    @extend_schema(request=None, responses={200: ProductDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        services.remove_product_branch_price(request.membership, public_id, scope=request.branch_scope)
        return self.product(public_id)


class StockAlertsView(APIView):
    """Stock bajo y perecederos por vencer de las sedes del alcance, cada uno con su producto para abrirlo."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "inventario.ver"

    @extend_schema(responses={200: StockAlertsSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        return Response(StockAlertsSerializer(stock_alerts(request.membership, scope=request.branch_scope)).data)
