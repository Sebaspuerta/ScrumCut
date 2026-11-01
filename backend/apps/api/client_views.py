"""API de Clientes (fase R3). Vistas delgadas: validan el formato con el formulario de la pantalla de Django y
llaman a los services de `apps.clients`, con el alcance de sede de la petición.

La persona es de la barbería (cualquier sede la encuentra y la edita); su historial, nivel y fiados son de las
sedes del alcance. Crear exige la autorización de la política de datos vigente (`create_client_with_current_policy`).
"""

from uuid import UUID

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.client_serializers import (
    ClientDetailSerializer,
    ClientListQuerySerializer,
    ClientListSerializer,
    ClientSerializer,
    ClientUpdateSerializer,
)
from apps.api.clients import client_detail, client_list, duplicate_error
from apps.api.permissions import HasRolePermission
from apps.api.serializers import OBJECT_READ_ERRORS, OBJECT_WRITE_ERRORS, READ_ERRORS, WRITE_ERRORS, query_values
from apps.clients import services
from apps.clients.board import ClientFilter
from apps.clients.forms import ClientForm, NewClientForm

FORM_FIELDS = ("full_name", "phone", "document", "email", "notes")
# Las claves de los errores del formulario y de los services, en los campos de la API.
ERROR_FIELDS = {field: field for field in (*FORM_FIELDS, "consent", "other_person")} | {"data_consent_at": "consent"}


class ClientListView(APIView):
    """La lista de la sede (?q=, ?nivel=, ?orden=, ?page=); la búsqueda encuentra a cualquier cliente de la barbería,
    sin cifras de otras sedes."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "clientes.ver"

    @extend_schema(
        operation_id="clients_list",
        parameters=[ClientListQuerySerializer],
        responses={200: ClientListSerializer, **READ_ERRORS},
    )
    def get(self, request: Request) -> Response:
        data = query_values(ClientListQuerySerializer, request.query_params)
        filters = ClientFilter(search=data["q"], level=data["nivel"], order=data["orden"])
        page = client_list(request.membership, scope=request.branch_scope, filters=filters, page=data["page"])
        return Response(ClientListSerializer(page).data)


class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "clientes.ver"

    @extend_schema(responses={200: ClientDetailSerializer, **OBJECT_READ_ERRORS})
    def get(self, request: Request, public_id: UUID) -> Response:
        data = client_detail(request.membership, public_id, scope=request.branch_scope)
        return Response(ClientDetailSerializer(data).data)


class ClientWriteView(APIView):
    """Cada escritura responde la ficha como queda, leída de nuevo por el alcance."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    error_fields = ERROR_FIELDS

    def form(self, serializer_class: type[serializers.Serializer], form_class: type[ClientForm]) -> ClientForm:
        """El mismo formulario de la pantalla de Django: el celular colombiano y, al crear, la autorización."""
        body = serializer_class(data=self.request.data)
        body.is_valid(raise_exception=True)
        form = form_class(body.validated_data)
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        return form

    def detail(self, public_id: UUID, status_code: int = status.HTTP_200_OK) -> Response:
        data = client_detail(self.request.membership, public_id, scope=self.request.branch_scope)
        return Response(ClientDetailSerializer(data).data, status=status_code)


class ClientCreateView(ClientWriteView):
    """Un duplicado responde el nombre del cliente que ya existe; uno con el mismo nombre se confirma con
    `other_person`."""

    required_permission = "clientes.crear"

    @extend_schema(request=ClientSerializer, responses={201: ClientDetailSerializer, **WRITE_ERRORS})
    def post(self, request: Request) -> Response:
        form = self.form(ClientSerializer, NewClientForm)
        try:
            client = services.create_client_with_current_policy(
                request.membership, form.client_data(), force=form.cleaned_data["other_person"]
            )
        except ValidationError as error:
            raise duplicate_error(error) from error
        return self.detail(client.public_id, status.HTTP_201_CREATED)


class ClientUpdateView(ClientWriteView):
    """Los datos de la persona, de la barbería; los cambios quedan en la auditoría (`update_client`)."""

    required_permission = "clientes.editar"

    @extend_schema(request=ClientUpdateSerializer, responses={200: ClientDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        form = self.form(ClientUpdateSerializer, ClientForm)
        try:
            services.update_client(request.membership, public_id, data=form.update_data())
        except ValidationError as error:
            raise duplicate_error(error) from error
        return self.detail(public_id)
