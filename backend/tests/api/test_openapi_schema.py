"""El esquema OpenAPI guardado es el que genera drf-spectacular: si la API cambia, hay que regenerarlo.

cd backend
python manage.py spectacular --format openapi-json --validate --fail-on-warn --file ../frontend/app/openapi.json
cd ../frontend/app && npm run gen:types
"""

import json

from django.conf import settings
from django.core.management import call_command

COMMITTED_SCHEMA = settings.FRONTEND_DIR / "app" / "openapi.json"


def test_el_esquema_guardado_coincide_con_la_api(tmp_path):
    generated = tmp_path / "openapi.json"
    call_command("spectacular", "--format", "openapi-json", "--validate", "--fail-on-warn", "--file", str(generated))

    assert json.loads(COMMITTED_SCHEMA.read_text(encoding="utf-8")) == json.loads(generated.read_text(encoding="utf-8"))
