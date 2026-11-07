"""Apoyo de las pruebas del inventario en la API: rutas por producto, cuerpos con llave y fotos de prueba."""

import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from apps.inventory.models import Product
from tests.api.sales_support import post


def product_url(name: str, product: Product) -> str:
    return reverse(name, kwargs={"public_id": product.public_id})


def move(client: Client, name: str, product: Product, **body):
    """Una entrada, un ajuste o un traslado, con una llave nueva salvo que la prueba traiga la suya."""
    return post(client, name, {"request_key": str(uuid.uuid4()), **body}, public_id=product.public_id)


def entry(client: Client, product: Product, quantity: int = 2, reason: str = "Compra", **body):
    return move(client, "api_product_entry", product, quantity=quantity, reason=reason, **body)


def photo_file(fmt: str = "PNG", size: tuple[int, int] = (300, 300)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 80, 40)).save(buffer, format=fmt)
    return SimpleUploadedFile(f"foto.{fmt.lower()}", buffer.getvalue())


def upload(client: Client, product: Product, file) -> object:
    """Multipart, como lo manda la app: el cliente de pruebas arma el cuerpo con su límite."""
    return client.post(product_url("api_product_photo_upload", product), {"photo": file})
