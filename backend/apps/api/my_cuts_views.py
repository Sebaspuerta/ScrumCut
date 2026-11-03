"""«Mis cortes» (fase R4): el barbero de la sesión, en la sede del alcance."""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.my_cuts import my_cuts_page
from apps.api.my_cuts_serializers import MyCutsQuerySerializer, MyCutsSerializer
from apps.api.permissions import HasRolePermission
from apps.api.serializers import READ_ERRORS, query_values


class MyCutsView(APIView):
    """Hoy, el mes y sus comandas cerradas del día (?fecha=); un valor inválido vuelve a hoy, como en Comandas."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "comandas.ver"

    @extend_schema(parameters=[MyCutsQuerySerializer], responses={200: MyCutsSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        query = query_values(MyCutsQuerySerializer, request.query_params)
        data = my_cuts_page(request.membership, scope=request.branch_scope, day=query["fecha"], page=query["page"])
        return Response(MyCutsSerializer(data).data)
