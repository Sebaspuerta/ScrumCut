"""Regenera frontend/app/openapi.json: el esquema de drf-spectacular, validado y con su salto de línea final.

`manage.py spectacular` escribe el archivo sin el salto de línea final y el hook end-of-file-fixer de
pre-commit lo corregiría a mano en cada cambio de la API; este comando lo deja listo de una vez.
"""

import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

SCHEMA_PATH = settings.FRONTEND_DIR / "app" / "openapi.json"


def render_schema() -> str:
    """El esquema como lo genera drf-spectacular (validado y sin advertencias), terminado en salto de línea."""
    with tempfile.TemporaryDirectory() as folder:
        generated = Path(folder) / "openapi.json"
        options = ("--format", "openapi-json", "--validate", "--fail-on-warn")
        call_command("spectacular", *options, "--file", str(generated))
        return generated.read_text(encoding="utf-8").rstrip("\n") + "\n"


class Command(BaseCommand):
    help = "Regenera frontend/app/openapi.json (después: npm run gen:types en frontend/app)."

    def handle(self, *args, **options) -> None:
        SCHEMA_PATH.write_text(render_schema(), encoding="utf-8", newline="\n")
        self.stdout.write(f"Esquema escrito en {SCHEMA_PATH}.")
