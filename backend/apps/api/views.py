"""API del marco de la app de React (fase R0). Vistas delgadas: el formato aquí, las reglas en tenancy y core."""

from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import set_theme
from apps.api import selectors
from apps.api.dashboard import dashboard
from apps.api.dashboard_serializers import DashboardQuerySerializer, DashboardSerializer
from apps.api.notifications import notifications
from apps.api.permissions import HasRolePermission
from apps.api.serializers import (
    READ_ERRORS,
    WRITE_ERRORS,
    BranchChoiceSerializer,
    BranchStateSerializer,
    CsrfSerializer,
    MeSerializer,
    NavigationSerializer,
    NotificationsSerializer,
    PreferencesSerializer,
)
from apps.tenancy.middleware import BRANCH_SESSION_KEY
from apps.tenancy.services import choose_branch


class MeView(APIView):
    """Solo sesión: quien aún no tiene barbería activa también debe saber quién es."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MeSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        data = selectors.me(request.user, request.membership, request.branch_scope)
        return Response(MeSerializer(data).data)


class NavigationView(APIView):
    """Cada ítem ya viene filtrado por el permiso del rol en `navigation.py`."""

    permission_classes = [IsAuthenticated, HasRolePermission]

    @extend_schema(responses={200: NavigationSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        data = selectors.navigation(request.membership, request.branch_scope)
        return Response(NavigationSerializer(data).data)


class BranchView(APIView):
    """Cambia la sede activa; una sede no permitida responde 403, como `switch_branch`."""

    permission_classes = [IsAuthenticated, HasRolePermission]

    @extend_schema(request=BranchChoiceSerializer, responses={200: BranchStateSerializer, **WRITE_ERRORS})
    def post(self, request: Request) -> Response:
        choice = BranchChoiceSerializer(data=request.data)
        choice.is_valid(raise_exception=True)
        scope = choose_branch(request.membership, choice.validated_data["sede"])
        request.session[BRANCH_SESSION_KEY] = scope.token
        return Response(BranchStateSerializer(selectors.branch_state(request.membership, scope)).data)


class CsrfView(APIView):
    """La cookie CSRF es HttpOnly: la app de React pide aquí el token y lo guarda solo en memoria."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CsrfSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        return Response(CsrfSerializer({"csrf_token": get_token(request)}).data)


class PreferencesView(APIView):
    """Preferencias de la propia persona; hoy, el tema. Se guardan en el servidor, nunca en el navegador."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=PreferencesSerializer, responses={200: PreferencesSerializer, **WRITE_ERRORS})
    def patch(self, request: Request) -> Response:
        preferences = PreferencesSerializer(data=request.data)
        preferences.is_valid(raise_exception=True)
        user = set_theme(request.user, preferences.validated_data["theme"])
        return Response(PreferencesSerializer({"theme": user.theme}).data)


class NotificationsView(APIView):
    """Solo lectura: las alertas sin resolver de la sede activa (o de todas en «todas»)."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "alertas.ver"

    @extend_schema(responses={200: NotificationsSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        data = notifications(request.membership, scope=request.branch_scope)
        return Response(NotificationsSerializer(data).data)


class DashboardView(APIView):
    """El tablero ejecutivo del mes (?mes=AAAA-MM) en el alcance de la sesión."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "reportes.ver"

    @extend_schema(
        parameters=[OpenApiParameter("mes", str, description="AAAA-MM; si no vale, el mes actual.")],
        responses={200: DashboardSerializer, **READ_ERRORS},
    )
    def get(self, request: Request) -> Response:
        query = DashboardQuerySerializer(data=request.query_params)
        month = query.validated_data.get("mes") if query.is_valid() else None
        data = dashboard(request.membership, scope=request.branch_scope, requested_month=month)
        return Response(DashboardSerializer(data).data)
