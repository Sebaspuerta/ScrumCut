"""Forma de las respuestas de la API. De aquí sale el esquema OpenAPI y, de él, los tipos de TypeScript."""

from rest_framework import serializers

from apps.accounts.models import Theme
from apps.alerts.models import AlertType
from apps.api.selectors import COMING, LINK, SOON
from apps.tenancy.branch_scope import ALL, ONE
from apps.tenancy.roles import Role

# Nombres de los enums en el esquema OpenAPI (SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]).
BRANCH_MODES = [ONE, ALL]
NAV_STATUSES = [LINK, SOON, COMING]


class UserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField()
    initials = serializers.CharField()
    theme = serializers.ChoiceField(choices=Theme.choices)


class BarbershopSerializer(serializers.Serializer):
    name = serializers.CharField()
    initials = serializers.CharField()
    timezone = serializers.CharField(help_text="Zona horaria de la barbería: «hoy» y las horas se leen en ella.")


class RoleSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=Role.choices)
    label = serializers.CharField()


class BranchOptionSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="El public_id de la sede: lo que se envía para elegirla.")
    label = serializers.CharField()
    current = serializers.BooleanField()


class BranchStateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=BRANCH_MODES)
    current_label = serializers.CharField(help_text="La sede actual o «Todas las sedes».")
    options = BranchOptionSerializer(many=True, help_text="Las sedes activas que la membresía puede elegir.")
    can_view_all = serializers.BooleanField(help_text="Con sedes.ver puede elegir «todas».")
    can_manage = serializers.BooleanField(help_text="Con sedes.gestionar.")


class MeSerializer(serializers.Serializer):
    user = UserSerializer()
    barbershop = BarbershopSerializer(allow_null=True)
    role = RoleSerializer(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())
    branch = BranchStateSerializer(allow_null=True)


class NavItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    icon = serializers.CharField(allow_null=True, help_text="Nombre del ícono de Lucide.")
    url = serializers.CharField(allow_null=True, help_text="La pantalla en plantillas; solo con el estado «enlace».")
    app_path = serializers.CharField(allow_null=True, help_text="La ruta en la app de React, si ya existe allí.")
    status = serializers.ChoiceField(choices=NAV_STATUSES)


class NavGroupSerializer(serializers.Serializer):
    title = serializers.CharField()
    items = NavItemSerializer(many=True)


class PlanUsageSerializer(serializers.Serializer):
    active = serializers.IntegerField()
    limit = serializers.IntegerField()


class LastChangeSerializer(serializers.Serializer):
    action = serializers.CharField()
    entity = serializers.CharField()
    actor = serializers.CharField()
    at = serializers.DateTimeField()


class AdministrationSummarySerializer(serializers.Serializer):
    branches = PlanUsageSerializer(allow_null=True, help_text="Con sedes.ver.")
    members = serializers.IntegerField(allow_null=True, help_text="Con usuarios.ver.")
    can_see_audit = serializers.BooleanField(help_text="Con auditoria.ver.")
    last_change = LastChangeSerializer(allow_null=True)


class NavigationSerializer(serializers.Serializer):
    sidebar = NavGroupSerializer(many=True)
    administration = NavGroupSerializer(many=True)
    administration_summary = AdministrationSummarySerializer(allow_null=True, help_text="Sin ítems, null.")
    new_actions = NavItemSerializer(many=True)
    unread_alerts = serializers.IntegerField(allow_null=True, help_text="Sin alertas.ver, null.")


class BranchChoiceSerializer(serializers.Serializer):
    """Solo el formato: qué sede se puede elegir lo decide `tenancy.services.choose_branch`."""

    sede = serializers.CharField(max_length=40, help_text="El token de una opción o «todas».")


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class PreferencesSerializer(serializers.Serializer):
    theme = serializers.ChoiceField(choices=Theme.choices)


class AlertItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=AlertType.choices)
    kind_label = serializers.CharField()
    message = serializers.CharField()
    branch = serializers.CharField()
    created_at = serializers.DateTimeField()
    unread = serializers.BooleanField()


class AlertGroupSerializer(serializers.Serializer):
    title = serializers.CharField()
    items = AlertItemSerializer(many=True)


class NotificationsSerializer(serializers.Serializer):
    unread = serializers.IntegerField()
    groups = AlertGroupSerializer(many=True, help_text="«Hoy» y «Anteriores», solo los que tienen alertas.")


class ApiErrorSerializer(serializers.Serializer):
    """La forma de todo error de /api/v1/ (`apps.api.exceptions`): el mensaje, qué pasó y los campos."""

    detail = serializers.CharField(help_text="Para el usuario: un texto fijo o el mensaje de la validación.")
    code = serializers.CharField(help_text="«invalid», «permission_denied», «not_found», «stale_session»…")
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()), help_text="Los mensajes de cada campo; o vacío."
    )


def error_responses(*statuses: int) -> dict[int, type[ApiErrorSerializer]]:
    """Las respuestas de error de una operación en el esquema, todas con la misma forma."""
    return dict.fromkeys(statuses, ApiErrorSerializer)


# Toda vista exige sesión (sin ella, 403 con SessionAuthentication) y tiene límite de peticiones (429).
READ_ERRORS = error_responses(403, 429)
WRITE_ERRORS = error_responses(400, 403, 429)
OBJECT_READ_ERRORS = error_responses(403, 404, 429)
OBJECT_WRITE_ERRORS = error_responses(400, 403, 404, 429)
