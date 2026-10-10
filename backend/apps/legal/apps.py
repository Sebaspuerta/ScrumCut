from django.apps import AppConfig


class LegalConfig(AppConfig):
    name = "apps.legal"
    label = "legal"

    def ready(self) -> None:
        from apps.legal import checks  # noqa: F401  registra el chequeo de despliegue
