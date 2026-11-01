"""API de Fiados (fase R3). Vistas delgadas sobre `apps.receivables`, los mismos selectores y services de la
pantalla de Django, con el alcance de sede de la petición.

Un fiado se abona solo en su sede de origen: el de otra sede no se encuentra (404) y en "todas" el abono responde
400 con el mensaje que pide elegir una sede. El abono pasa por `add_payment` y de ahí por `record_money`.
"""

from uuid import UUID

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasRolePermission
from apps.api.receivable_serializers import (
    ReceivableDetailSerializer,
    ReceivableListQuerySerializer,
    ReceivableListSerializer,
    ReceivablePaymentSerializer,
)
from apps.api.receivables import receivable_data, receivable_list
from apps.api.serializers import OBJECT_READ_ERRORS, OBJECT_WRITE_ERRORS, READ_ERRORS, query_values
from apps.cash.selectors import payment_methods
from apps.receivables import services
from apps.receivables.board import ReceivableFilter
from apps.receivables.forms import PaymentForm


class ReceivableListView(APIView):
    """La cartera de la sede y una pestaña (?pestana=pendientes|vencidos|pagados, ?q=, ?page=)."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "fiados.ver"

    @extend_schema(
        operation_id="receivables_list",
        parameters=[ReceivableListQuerySerializer],
        responses={200: ReceivableListSerializer, **READ_ERRORS},
    )
    def get(self, request: Request) -> Response:
        data = query_values(ReceivableListQuerySerializer, request.query_params)
        filters = ReceivableFilter(tab=data["pestana"], search=data["q"])
        page = receivable_list(request.membership, scope=request.branch_scope, filters=filters, page=data["page"])
        return Response(ReceivableListSerializer(page).data)


class ReceivableDetailView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "fiados.ver"

    @extend_schema(responses={200: ReceivableDetailSerializer, **OBJECT_READ_ERRORS})
    def get(self, request: Request, public_id: UUID) -> Response:
        data = receivable_data(request.membership, public_id, scope=request.branch_scope)
        return Response(ReceivableDetailSerializer(data).data)


def _payment_form(data: dict) -> PaymentForm:
    """El mismo formulario del abono de Django: valida que la forma de pago esté habilitada."""
    form = PaymentForm(
        {
            "monto": data["amount"],
            "metodo": data["method"],
            "referencia": data["reference"],
            "nota": data["note"],
            "saldo_visto": data["expected_balance"],
        },
        methods=payment_methods(),
    )
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    return form


class ReceivablePayView(APIView):
    """Parcial o total. Un segundo envío del mismo abono se rechaza: ya no ve el saldo que vio el primero."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "fiados.abonar"
    error_fields = {
        "monto": "amount",
        "amount": "amount",
        "metodo": "method",
        "referencia": "reference",
        "nota": "note",
        "saldo_visto": "expected_balance",
    }

    @extend_schema(
        request=ReceivablePaymentSerializer, responses={200: ReceivableDetailSerializer, **OBJECT_WRITE_ERRORS}
    )
    def post(self, request: Request, public_id: UUID) -> Response:
        body = ReceivablePaymentSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        payment = _payment_form(body.validated_data).cleaned_data
        services.add_payment(
            request.membership,
            public_id,
            scope=request.branch_scope,
            amount=payment["monto"],
            method=payment["metodo"],
            reference=payment["referencia"],
            note=payment["nota"],
            expected_balance=payment["saldo_visto"],
        )
        data = receivable_data(request.membership, public_id, scope=request.branch_scope)
        return Response(ReceivableDetailSerializer(data).data)
