"""La foto del producto en la API: se sube por multipart con CSRF y la valida `upload_product_photo`; se sirve solo
por la API, con sesión e inventario.ver, de la barbería de la sesión (si no, 404) y con Cache-Control privado."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.core.tenant_context import tenant_context
from apps.inventory import services
from apps.inventory.models import Product
from apps.tenancy.roles import Role
from tests.api.inventory_support import photo_file, product_url, upload
from tests.inventory.helpers import make_product

pytestmark = pytest.mark.django_db

FIVE_MB = 5 * 1024 * 1024


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _served(client: Client, path: str):
    response = client.get(path)
    body = b"".join(response.streaming_content) if response.status_code == 200 else b""
    return response, body


def test_la_foto_se_sube_y_se_sirve_por_la_api_con_cache_privado(world, owner_client):
    uploaded = upload(owner_client, world.cera, photo_file("JPEG"))

    path = uploaded.json()["photo"]
    response, body = _served(owner_client, path)

    assert uploaded.status_code == 200
    assert path.startswith(product_url("api_product_photo", world.cera))
    assert (response.status_code, response["Content-Type"], response["Cache-Control"]) == (
        200,
        "image/webp",
        "private, max-age=86400",
    )
    assert body[:4] == b"RIFF" and body[8:12] == b"WEBP"


def test_la_foto_nunca_sale_por_la_url_publica_de_media(world, owner_client, settings):
    upload(owner_client, world.cera, photo_file())
    stored = Product.objects.get(pk=world.cera.pk).photo.name

    assert owner_client.get(f"{settings.MEDIA_URL}{stored}").status_code == 404


def test_la_foto_exige_sesion_y_permiso(world, owner_client):
    path = upload(owner_client, world.cera, photo_file()).json()["photo"]

    assert Client().get(path).status_code in {401, 403}
    assert Client().post(product_url("api_product_photo_upload", world.cera), {"photo": photo_file()}).status_code in {
        401,
        403,
    }


@pytest.mark.parametrize("role", [Role.CASHIER, Role.VIEWER])
def test_quien_solo_ve_el_inventario_ve_la_foto_pero_no_la_cambia(world, owner_client, member, role):
    path = upload(owner_client, world.cera, photo_file()).json()["photo"]
    login = world.cashier if role == Role.CASHIER else member(role, world.shop)
    client = Client()
    client.force_login(login.user)

    assert _served(client, path)[0].status_code == 200
    assert upload(client, world.cera, photo_file()).status_code == 403


def test_la_foto_de_otra_barberia_responde_404(world, owner_client, member, other_shop):
    with tenant_context(other_shop.pk):
        their_owner = member(Role.OWNER, other_shop)
        theirs = make_product(their_owner, name="Cera ajena")
        services.upload_product_photo(their_owner, theirs.public_id, upload=photo_file())

    assert owner_client.get(product_url("api_product_photo", theirs)).status_code == 404
    assert upload(owner_client, theirs, photo_file()).status_code == 404


def test_un_producto_sin_foto_responde_404(world, owner_client):
    assert owner_client.get(product_url("api_product_photo", world.cera)).status_code == 404


@pytest.mark.parametrize(
    ("file", "message"),
    [
        (SimpleUploadedFile("foto.png", b"esto no es una imagen"), "El archivo no es una imagen válida."),
        (SimpleUploadedFile("foto.png", b"\x89PNG" + b"\x00" * FIVE_MB), services.PHOTO_TOO_LARGE),
        (SimpleUploadedFile("foto.png", b"\x89PNG" + b"\x00" * (2 * FIVE_MB)), services.PHOTO_TOO_LARGE),
    ],
    ids=["no_es_imagen", "pasa_de_5_mb", "peticion_demasiado_grande"],
)
def test_un_archivo_que_no_es_imagen_o_pasa_de_5_mb_se_rechaza(world, owner_client, file, message):
    response = upload(owner_client, world.cera, file)

    assert (response.status_code, response.json()["field_errors"]) == (400, {"photo": [message]})
    assert not Product.objects.get(pk=world.cera.pk).photo


def test_la_subida_exige_csrf(world, owner_client):
    client = Client(enforce_csrf_checks=True)
    client.cookies = owner_client.cookies
    url = product_url("api_product_photo_upload", world.cera)

    rejected = client.post(url, {"photo": photo_file()})
    token = client.get(reverse("api_csrf")).json()["csrf_token"]
    accepted = client.post(url, {"photo": photo_file()}, HTTP_X_CSRFTOKEN=token)

    assert (rejected.status_code, rejected.json()["code"]) == (403, "csrf_failed")
    assert accepted.status_code == 200
