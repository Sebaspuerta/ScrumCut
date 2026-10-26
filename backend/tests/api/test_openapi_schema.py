"""El esquema OpenAPI guardado es el que genera drf-spectacular: si la API cambia, hay que regenerarlo.

cd backend
python manage.py openapi_schema
cd ../frontend/app && npm run gen:types
"""

from apps.api.management.commands.openapi_schema import SCHEMA_PATH, render_schema


def test_el_esquema_guardado_coincide_con_la_api_byte_a_byte():
    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_schema()


def test_el_esquema_termina_con_un_salto_de_linea():
    assert SCHEMA_PATH.read_bytes().endswith(b"}\n")
