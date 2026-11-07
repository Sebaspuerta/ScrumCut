"""Forma del inventario en la API. Las peticiones solo validan el formato con los topes de las columnas; las reglas
(stock nunca negativo, motivo obligatorio, sede de destino, precio por sede, foto real) están en `apps.inventory`."""

from uuid import UUID

from rest_framework import serializers

from apps.api.fields import MoneyInput, money
from apps.api.inventory import STATUSES, UNCATEGORIZED
from apps.api.order_serializers import OptionSerializer
from apps.inventory.models import MAX_QUANTITY, Product, ProductCategory, ProductType

_PRODUCT = Product._meta
REASON_MAX_LENGTH = 200
REQUEST_KEY_HELP = "La llave del intento: la misma en cada reintento, otra para un movimiento nuevo."


class ProductListQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, max_length=60, default="", help_text="Nombre o proveedor.")
    categoria = serializers.CharField(
        required=False, allow_blank=True, default="", help_text=f"El id de una categoría o «{UNCATEGORIZED}»."
    )
    tipo = serializers.ChoiceField(choices=ProductType.choices, required=False, allow_blank=True, default="")
    estado = serializers.ChoiceField(choices=STATUSES, required=False, default=STATUSES[0][0])
    page = serializers.IntegerField(required=False, min_value=1, default=1)

    def validate_categoria(self, value: str) -> str:
        if value in {"", UNCATEGORIZED}:
            return value
        try:
            return str(UUID(value))
        except ValueError as exc:
            raise serializers.ValidationError("Categoría inválida.") from exc


class ProductDetailQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1, help_text="La página de movimientos.")


class StockLevelSerializer(serializers.Serializer):
    branch = serializers.CharField()
    quantity = serializers.IntegerField()
    low = serializers.BooleanField(help_text="En o por debajo del mínimo del producto.")


class InventoryProductSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    product_type = serializers.ChoiceField(choices=ProductType.choices)
    type_label = serializers.CharField()
    photo = serializers.CharField(allow_null=True, help_text="La ruta de la foto en la API; sin foto, null.")
    stock = serializers.IntegerField(help_text="En la sede del alcance; en «todas», la suma de las sedes.")
    price = money(help_text="El precio efectivo: el de la sede o el del catálogo; en «todas», el del catálogo.")
    minimum_stock = serializers.IntegerField(allow_null=True)
    low_stock = serializers.BooleanField(help_text="Alguna sede del alcance está en o bajo el mínimo.")
    is_active = serializers.BooleanField()
    levels = StockLevelSerializer(many=True, help_text="Las existencias de cada sede del alcance.")


class ProductListSerializer(serializers.Serializer):
    search = serializers.CharField()
    category = serializers.CharField()
    product_type = serializers.CharField()
    status = serializers.CharField()
    categories = OptionSerializer(many=True)
    types = OptionSerializer(many=True)
    statuses = OptionSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField(help_text="Productos por página.")
    results = InventoryProductSerializer(many=True)


class CategoryRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class MovementSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    at = serializers.DateTimeField()
    kind = serializers.CharField()
    kind_label = serializers.CharField()
    branch = serializers.CharField()
    quantity = serializers.IntegerField(help_text="Con signo: + entra, − sale.")
    stock_before = serializers.IntegerField()
    stock_after = serializers.IntegerField()
    unit_cost = money()
    reason = serializers.CharField()
    by = serializers.CharField()


class MovementPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = MovementSerializer(many=True)


class DestinationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    stock = serializers.IntegerField(help_text="Lo que ya hay del producto en esa sede.")


class ProductActionsSerializer(serializers.Serializer):
    edit = serializers.BooleanField()
    delete = serializers.BooleanField()
    adjust = serializers.BooleanField(help_text="Entrada, ajuste y traslado: con inventario.ajustar y una sede.")
    branch_price = serializers.BooleanField(help_text="Fijar o quitar el precio de la sede: con una sede.")


class ProductDetailSerializer(InventoryProductSerializer):
    category = CategoryRefSerializer(allow_null=True)
    purchase_cost = money()
    sale_price = money(help_text="El precio del catálogo.")
    branch_price = money(allow_null=True, help_text="El precio propio de la sede; sin él, null.")
    expiration_date = serializers.DateField(allow_null=True)
    supplier = serializers.CharField()
    branch = serializers.CharField(allow_null=True, help_text="La sede del alcance; en «todas», null.")
    movements = MovementPageSerializer()
    destinations = DestinationSerializer(many=True, help_text="Las sedes a las que se puede trasladar.")
    actions = ProductActionsSerializer()
    needs_branch = serializers.BooleanField(help_text="Puede mover stock, pero en «todas» primero elige una sede.")


class AlertLevelSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    name = serializers.CharField()
    branch = serializers.CharField()
    quantity = serializers.IntegerField()
    minimum_stock = serializers.IntegerField(allow_null=True)
    expiration_date = serializers.DateField(allow_null=True)
    expired = serializers.BooleanField()


class StockAlertsSerializer(serializers.Serializer):
    low_stock = AlertLevelSerializer(many=True, help_text="Los más bajos primero.")
    low_stock_count = serializers.IntegerField()
    expiring = AlertLevelSerializer(many=True, help_text="Los que vencen antes primero; incluye los vencidos.")
    expiring_count = serializers.IntegerField()


class CategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=ProductCategory._meta.get_field("name").max_length, allow_blank=True)


class CategoryDeleteSerializer(serializers.Serializer):
    delete_products = serializers.BooleanField(help_text="True borra sus productos; False los deja sin categoría.")


class CategoryListSerializer(serializers.Serializer):
    results = CategoryRefSerializer(many=True)


class ProductSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=_PRODUCT.get_field("name").max_length, allow_blank=True)
    category = serializers.UUIDField(allow_null=True, required=False, default=None)
    product_type = serializers.ChoiceField(choices=ProductType.choices)
    purchase_cost = MoneyInput()
    sale_price = MoneyInput()
    minimum_stock = serializers.IntegerField(min_value=0, max_value=MAX_QUANTITY, allow_null=True, default=None)
    expiration_date = serializers.DateField(allow_null=True, required=False, default=None)
    supplier = serializers.CharField(
        max_length=_PRODUCT.get_field("supplier").max_length, allow_blank=True, required=False, default=""
    )


class ProductCreateSerializer(ProductSerializer):
    initial_stock = serializers.IntegerField(
        min_value=0, max_value=MAX_QUANTITY, default=0, help_text="Entra en la sede del alcance."
    )


class ProductDeletedSerializer(serializers.Serializer):
    id = serializers.UUIDField()


class ActiveSerializer(serializers.Serializer):
    active = serializers.BooleanField()


class BranchPriceSerializer(serializers.Serializer):
    price = MoneyInput(help_text="El precio de venta en la sede del alcance.")


class PhotoUploadSerializer(serializers.Serializer):
    """Solo que llegue un archivo: el formato, el peso y que sea una imagen real los valida `upload_product_photo`."""

    photo = serializers.FileField(allow_empty_file=True, help_text="PNG, JPEG o WEBP de hasta 5 MB.")


class _StockRequestSerializer(serializers.Serializer):
    request_key = serializers.UUIDField(help_text=REQUEST_KEY_HELP)
    reason = serializers.CharField(max_length=REASON_MAX_LENGTH, allow_blank=True, help_text="Obligatorio.")


class EntrySerializer(_StockRequestSerializer):
    quantity = serializers.IntegerField(max_value=MAX_QUANTITY, help_text="Mayor que cero.")
    unit_cost = MoneyInput(allow_null=True, required=False, default=None, help_text="Sin él, el costo del producto.")


class AdjustmentSerializer(_StockRequestSerializer):
    quantity = serializers.IntegerField(
        min_value=-MAX_QUANTITY, max_value=MAX_QUANTITY, help_text="Con signo: + suma, − resta. Nunca cero."
    )


class TransferSerializer(_StockRequestSerializer):
    destination = serializers.UUIDField(help_text="Otra sede activa de la barbería.")
    quantity = serializers.IntegerField(max_value=MAX_QUANTITY, help_text="Mayor que cero.")
