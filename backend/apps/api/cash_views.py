"""API de Caja (fase R2). Vistas delgadas sobre los services de `apps.cash`, los mismos de la pantalla de Django.

Siempre de una sede: abrir exige una (`branch_for_write`) y la caja de otra sede no se encuentra (404). Una
caja de otro día no recibe movimientos en efectivo (`record_money` la rechaza) y solo se cierra.
"""

from uuid import UUID

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.cash import cash_state, closing_row, closings
from apps.api.cash_serializers import (
    CashQuerySerializer,
    CashStateSerializer,
    CloseCashSerializer,
    ClosingSerializer,
    ClosingsQuerySerializer,
    ClosingsSerializer,
    ManualMovementSerializer,
    OpenCashSerializer,
)
from apps.api.permissions import HasRolePermission
from apps.api.serializers import OBJECT_WRITE_ERRORS, READ_ERRORS, WRITE_ERRORS
from apps.cash import services
from apps.cash.board import closings_page
from apps.cash.choices import PaymentMethod
from apps.cash.forms import BILLS, CloseSessionForm, bill_field


class CashView(APIView):
    """La caja de la sede del alcance; ?tipo= filtra los movimientos, como en la pantalla de Django."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "caja.ver"

    @extend_schema(parameters=[CashQuerySerializer], responses={200: CashStateSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        query = CashQuerySerializer(data=request.query_params)
        kind = (query.validated_data["tipo"] or None) if query.is_valid() else None
        return Response(CashStateSerializer(cash_state(request.membership, scope=request.branch_scope, kind=kind)).data)


class CashClosingsView(APIView):
    """El historial de cierres de la sede, por páginas."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "caja.ver"

    @extend_schema(parameters=[ClosingsQuerySerializer], responses={200: ClosingsSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        query = ClosingsQuerySerializer(data=request.query_params)
        number = query.validated_data["page"] if query.is_valid() else 1
        page = closings_page(request.membership, scope=request.branch_scope, page=number)
        return Response(ClosingsSerializer(closings(page)).data)


class CashWriteView(APIView):
    """Cada escritura responde la caja como queda. `error_fields` traduce las claves de los errores de los
    services a los campos de la API (`apps.api.exceptions`)."""

    error_fields: dict[str, str] = {}

    permission_classes = [IsAuthenticated, HasRolePermission]

    def valid(self, serializer_class: type[serializers.Serializer]) -> dict:
        body = serializer_class(data=self.request.data)
        body.is_valid(raise_exception=True)
        return body.validated_data

    def state(self, status_code: int = status.HTTP_200_OK) -> Response:
        data = cash_state(self.request.membership, scope=self.request.branch_scope, kind=None)
        return Response(CashStateSerializer(data).data, status=status_code)


class CashOpenView(CashWriteView):
    required_permission = "caja.abrir"

    @extend_schema(request=OpenCashSerializer, responses={201: CashStateSerializer, **WRITE_ERRORS})
    def post(self, request: Request) -> Response:
        data = self.valid(OpenCashSerializer)
        services.open_session(request.membership, request.branch_scope, opening_amount=data["opening_amount"])
        return self.state(status.HTTP_201_CREATED)


class CashMovementView(CashWriteView):
    """Ingreso, gasto o retiro en efectivo de la caja abierta; `record_money` rechaza la de otro día."""

    required_permission = "caja.movimiento"
    error_fields = {"kind": "kind", "amount": "amount", "description": "description"}

    @extend_schema(request=ManualMovementSerializer, responses={201: CashStateSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, session: UUID) -> Response:
        data = self.valid(ManualMovementSerializer)
        services.register_manual_movement(
            request.membership,
            session,
            scope=request.branch_scope,
            kind=data["kind"],
            amount=data["amount"],
            payment_method=PaymentMethod.CASH,
            description=data["description"],
        )
        return self.state(status.HTTP_201_CREATED)


def _count_form(data: dict) -> CloseSessionForm:
    """El mismo formulario del arqueo de Django: suma los billetes y las monedas en el servidor."""
    fields = {bill_field(bill): 0 for bill in BILLS}
    fields |= {bill_field(row["denomination"]): row["count"] for row in data["bills"]}
    form = CloseSessionForm({**fields, "monedas": data["coins"], "nota": data["notes"]})
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    return form


class CashCloseView(CashWriteView):
    """Con diferencia entre el contado y el esperado, `close_session` exige la nota."""

    required_permission = "caja.cerrar"
    error_fields = {"notes": "notes", "nota": "notes", "monedas": "coins"} | {
        bill_field(bill): "bills" for bill in BILLS
    }

    @extend_schema(request=CloseCashSerializer, responses={200: ClosingSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, session: UUID) -> Response:
        data = self.valid(CloseCashSerializer)
        form = _count_form(data)
        closed = services.close_session(
            request.membership, session, scope=request.branch_scope, counted_amount=form.counted(), notes=data["notes"]
        )
        return Response(ClosingSerializer(closing_row(closed)).data)
