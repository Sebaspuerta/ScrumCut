"""Publica documentos de prueba para que `check --deploy` corra completo en la base desechable del CI."""

import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.legal.models import LegalDocument
from apps.legal.selectors import REQUIRED_FOR_SIGNUP

CI_VERSION = "ci"


class Command(BaseCommand):
    help = "Solo CI: publica términos, política de datos y aviso de privacidad de prueba."

    def handle(self, *args, **options) -> None:
        # GitHub Actions define CI=true. En otra base, un documento de prueba abriría el registro de verdad.
        if os.environ.get("CI") != "true":
            raise CommandError("Este comando solo corre en integración continua (CI=true).")
        for kind in REQUIRED_FOR_SIGNUP:
            LegalDocument.objects.get_or_create(
                kind=kind,
                version=CI_VERSION,
                defaults={"body": "Documento de prueba de CI.", "published_at": timezone.now()},
            )
        self.stdout.write(f"{len(REQUIRED_FOR_SIGNUP)} documentos de prueba de CI publicados.")
