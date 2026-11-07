"""API de Inventario (fase R7): categorías, productos y su foto. Vistas delgadas: validan el formato y llaman a los
services de `apps.inventory`, con el alcance de sede de la petición.

El catálogo es de la barbería: crear, editar y borrar productos o categorías se puede desde cualquier alcance. El
stock inicial de un producto nuevo entra en la sede del alcance (en «todas», solo sin stock). Un producto de otra
barbería no se encuentra (404), tampoco su foto.
"""

from pathlib import PurePath
from uuid import UUID

from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.inventory import ProductFilter, product_detail, product_list
from apps.api.inventory_serializers import (
    ActiveSerializer,
    CategoryDeleteSerializer,
    CategoryListSerializer,
    CategorySerializer,
    PhotoUploadSerializer,
    ProductCreateSerializer,
    ProductDeletedSerializer,
    ProductDetailQuerySerializer,
    ProductDetailSerializer,
    ProductListQuerySerializer,
    ProductListSerializer,
    ProductSerializer,
)
from apps.api.permissions import HasRolePermission
from apps.api.serializers import OBJECT_READ_ERRORS, OBJECT_WRITE_ERRORS, READ_ERRORS, WRITE_ERRORS, query_values
from apps.inventory import selectors, services

PRODUCT_FIELDS = (
    "name",
    "category",
    "product_type",
    "purchase_cost",
    "sale_price",
    "minimum_stock",
    "expiration_date",
    "supplier",
    "initial_stock",
    "photo",
)
# Las fotos que guarda `upload_product_photo` (WEBP) y las de antes (PNG): el tipo sale de la extensión guardada.
PHOTO_CONTENT_TYPES = {".webp": "image/webp", ".png": "image/png"}
# El navegador guarda la foto un día: su ruta cambia con cada edición del producto (`photo_url`).
PHOTO_CACHE = "private, max-age=86400"
# Lo que suman al archivo los límites y encabezados del multipart: con más, la petición no se lee.
MULTIPART_OVERHEAD = 64 * 1024


class InventoryWriteView(APIView):
    """Cada escritura de un producto responde el producto como queda, leído de nuevo por el alcance."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    error_fields = {field: field for field in PRODUCT_FIELDS}

    def valid(self, serializer_class: type[serializers.Serializer]) -> dict:
        body = serializer_class(data=self.request.data)
        body.is_valid(raise_exception=True)
        return body.validated_data

    def product(self, public_id: UUID, status_code: int = status.HTTP_200_OK) -> Response:
        data = product_detail(self.request.membership, public_id, scope=self.request.branch_scope)
        return Response(ProductDetailSerializer(data).data, status=status_code)


# ── Categorías ───────────────────────────────────────────────────────────────


def _categories(request: Request) -> Response:
    categories = selectors.list_categories(request.membership)
    data = {"results": [{"id": category.public_id, "name": category.name} for category in categories]}
    return Response(CategoryListSerializer(data).data)


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "inventario.ver"

    @extend_schema(operation_id="inventory_categories_list", responses={200: CategoryListSerializer, **READ_ERRORS})
    def get(self, request: Request) -> Response:
        return _categories(request)


class CategoryCreateView(InventoryWriteView):
    required_permission = "inventario.crear"
    error_fields = {"name": "name"}

    @extend_schema(request=CategorySerializer, responses={200: CategoryListSerializer, **WRITE_ERRORS})
    def post(self, request: Request) -> Response:
        services.create_category(request.membership, name=self.valid(CategorySerializer)["name"])
        return _categories(request)


class CategoryUpdateView(InventoryWriteView):
    required_permission = "inventario.editar"
    error_fields = {"name": "name"}

    @extend_schema(request=CategorySerializer, responses={200: CategoryListSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        services.update_category(request.membership, public_id, name=self.valid(CategorySerializer)["name"])
        return _categories(request)


class CategoryDeleteView(InventoryWriteView):
    """Regla 37: sus productos quedan sin categoría o se borran con ella, según `delete_products`."""

    required_permission = "inventario.eliminar"

    @extend_schema(request=CategoryDeleteSerializer, responses={200: CategoryListSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        data = self.valid(CategoryDeleteSerializer)
        services.soft_delete_category(request.membership, public_id, delete_products=data["delete_products"])
        return _categories(request)


# ── Productos ────────────────────────────────────────────────────────────────


class ProductListView(APIView):
    """El catálogo con la existencia y el precio de la sede (?q=, ?categoria=, ?tipo=, ?estado=, ?page=)."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "inventario.ver"

    @extend_schema(
        operation_id="products_list",
        parameters=[ProductListQuerySerializer],
        responses={200: ProductListSerializer, **READ_ERRORS},
    )
    def get(self, request: Request) -> Response:
        data = query_values(ProductListQuerySerializer, request.query_params)
        filters = ProductFilter(
            search=data["q"], category=data["categoria"], product_type=data["tipo"], status=data["estado"]
        )
        page = product_list(request.membership, scope=request.branch_scope, filters=filters, page=data["page"])
        return Response(ProductListSerializer(page).data)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "inventario.ver"

    @extend_schema(
        parameters=[ProductDetailQuerySerializer], responses={200: ProductDetailSerializer, **OBJECT_READ_ERRORS}
    )
    def get(self, request: Request, public_id: UUID) -> Response:
        page = query_values(ProductDetailQuerySerializer, request.query_params)["page"]
        data = product_detail(request.membership, public_id, scope=request.branch_scope, page=page)
        return Response(ProductDetailSerializer(data).data)


class ProductCreateView(InventoryWriteView):
    required_permission = "inventario.crear"

    @extend_schema(request=ProductCreateSerializer, responses={201: ProductDetailSerializer, **WRITE_ERRORS})
    def post(self, request: Request) -> Response:
        data = dict(self.valid(ProductCreateSerializer))
        initial_stock = data.pop("initial_stock")
        product = services.create_product(
            request.membership, data, scope=request.branch_scope, initial_stock=initial_stock
        )
        return self.product(product.public_id, status.HTTP_201_CREATED)


class ProductUpdateView(InventoryWriteView):
    """Los datos del catálogo; las existencias no: las cambian solo las entradas, los ajustes y los traslados."""

    required_permission = "inventario.editar"

    @extend_schema(request=ProductSerializer, responses={200: ProductDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        services.update_product(request.membership, public_id, data=dict(self.valid(ProductSerializer)))
        return self.product(public_id)


class ProductActiveView(InventoryWriteView):
    required_permission = "inventario.editar"

    @extend_schema(request=ActiveSerializer, responses={200: ProductDetailSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        change = services.activate_product if self.valid(ActiveSerializer)["active"] else services.deactivate_product
        change(request.membership, public_id)
        return self.product(public_id)


class ProductDeleteView(InventoryWriteView):
    """Regla 35: borrado lógico; sus ventas y movimientos quedan."""

    required_permission = "inventario.eliminar"

    @extend_schema(request=None, responses={200: ProductDeletedSerializer, **OBJECT_WRITE_ERRORS})
    def post(self, request: Request, public_id: UUID) -> Response:
        product = services.soft_delete_product(request.membership, public_id)
        return Response(ProductDeletedSerializer({"id": product.public_id}).data)


# ── Foto ─────────────────────────────────────────────────────────────────────


class ProductPhotoView(APIView):
    """La foto, solo con sesión e inventario.ver y solo de la barbería de la sesión (si no, 404). Nunca por MEDIA."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "inventario.ver"

    @extend_schema(
        responses={(200, "image/webp"): OpenApiResponse(OpenApiTypes.BINARY), **OBJECT_READ_ERRORS},
    )
    def get(self, request: Request, public_id: UUID) -> FileResponse:
        product = selectors.get_product(request.membership, public_id, scope=request.branch_scope)
        content_type = PHOTO_CONTENT_TYPES.get(PurePath(product.photo.name).suffix) if product.photo else None
        if content_type is None:
            raise Http404
        response = FileResponse(product.photo.open("rb"), content_type=content_type)
        response["Cache-Control"] = PHOTO_CACHE
        return response


def _declared_length(request: Request) -> int:
    """El largo que declara la petición; uno inválido lo rechaza después el lector del multipart (400)."""
    try:
        return int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return 0


class ProductPhotoUploadView(InventoryWriteView):
    """Multipart con CSRF. Una petición más grande que la foto permitida se rechaza antes de leerla."""

    required_permission = "inventario.editar"
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": PhotoUploadSerializer},
        responses={200: ProductDetailSerializer, **OBJECT_WRITE_ERRORS},
    )
    def post(self, request: Request, public_id: UUID) -> Response:
        if _declared_length(request) > services.PHOTO_MAX_BYTES + MULTIPART_OVERHEAD:
            raise ValidationError({"photo": services.PHOTO_TOO_LARGE})
        upload = self.valid(PhotoUploadSerializer)["photo"]
        services.upload_product_photo(request.membership, public_id, upload=upload)
        return self.product(public_id)
