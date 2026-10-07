"""Inventario de cada barbería: productos, movimientos de stock e insumos de servicios.

Portado de MAGNUS v1 (`models/inventory.py`, `category.py`, `service_consumable.py`)
según `docs/migracion-magnus.md`. Decisión 1: el stock es por barbería. El stock
solo cambia con un `StockMovement` (defecto 15) y nunca queda negativo (defecto 14).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import AppendOnlyModel, SoftDeleteModel, TenantScopedModel

_ALIVE = models.Q(deleted_at__isnull=True)
_MONEY = {"max_digits": 14, "decimal_places": 2, "validators": [MinValueValidator(Decimal("0"))]}


def product_photo_path(product: "Product", filename: str) -> str:
    # Ruta por barbería y producto; el nombre que manda el usuario se descarta.
    return f"barbershops/{product.barbershop.public_id}/products/{product.public_id}.png"


class ProductCategory(TenantScopedModel, SoftDeleteModel):
    name = models.CharField("nombre", max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                models.F("barbershop"),
                Lower("name"),
                condition=_ALIVE,
                name="uq_productcategory_name_per_barbershop",
                violation_error_message="Ya existe una categoría con ese nombre.",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ProductType(models.TextChoices):
    SALE = "venta", "Venta"
    CONSUMABLE = "consumible", "Consumible interno"
    PERISHABLE = "perecedero", "Perecedero"


class Product(TenantScopedModel, SoftDeleteModel):
    name = models.CharField("nombre", max_length=120)
    category = models.ForeignKey(
        ProductCategory, null=True, blank=True, on_delete=models.PROTECT, related_name="products"
    )
    product_type = models.CharField("tipo", max_length=12, choices=ProductType.choices)
    purchase_cost = models.DecimalField("costo de compra", default=Decimal("0"), **_MONEY)
    sale_price = models.DecimalField("precio de venta", default=Decimal("0"), **_MONEY)
    # Solo lo cambia services.apply_stock_movement.
    current_stock = models.IntegerField("stock actual", default=0, editable=False)
    minimum_stock = models.PositiveIntegerField("stock mínimo", null=True, blank=True)
    expiration_date = models.DateField("vence", null=True, blank=True)
    supplier = models.CharField("proveedor", max_length=120, blank=True)
    photo = models.ImageField("foto", upload_to=product_photo_path, blank=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                models.F("barbershop"),
                Lower("name"),
                condition=_ALIVE,
                name="uq_product_name_per_barbershop",
                violation_error_message="Ya existe un producto con ese nombre.",
            ),
            models.CheckConstraint(condition=models.Q(current_stock__gte=0), name="ck_product_stock_not_negative"),
            models.CheckConstraint(condition=models.Q(purchase_cost__gte=0), name="ck_product_cost_not_negative"),
            models.CheckConstraint(condition=models.Q(sale_price__gte=0), name="ck_product_price_not_negative"),
            models.CheckConstraint(
                condition=models.Q(product_type__in=ProductType.values), name="ck_product_type_valid"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class MovementType(models.TextChoices):
    ENTRY = "entrada", "Entrada"
    ADJUSTMENT = "ajuste", "Ajuste"
    SALE = "salida_venta", "Salida por venta"
    SERVICE = "salida_servicio", "Insumo de servicio"
    REVERSAL = "reversion", "Reversión"


class StockMovement(AppendOnlyModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField("tipo", max_length=16, choices=MovementType.choices)
    quantity = models.IntegerField("cantidad")  # con signo: + entra, − sale
    stock_before = models.IntegerField("stock antes")
    stock_after = models.IntegerField("stock después")
    unit_cost = models.DecimalField("costo unitario", **_MONEY)
    reason = models.TextField("motivo")
    # Origen del movimiento ("order:<public_id>"), para revertirlo exacto sin que inventario dependa de sales.
    reference = models.CharField("referencia", max_length=64, blank=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(quantity=0), name="ck_stockmovement_quantity_not_zero"),
            models.CheckConstraint(condition=models.Q(stock_after__gte=0), name="ck_stockmovement_stock_not_negative"),
            models.CheckConstraint(
                condition=models.Q(stock_after=models.F("stock_before") + models.F("quantity")),
                name="ck_stockmovement_stock_adds_up",
            ),
            models.CheckConstraint(condition=~models.Q(reason=""), name="ck_stockmovement_reason_present"),
            models.CheckConstraint(
                condition=models.Q(movement_type__in=MovementType.values), name="ck_stockmovement_type_valid"
            ),
        ]
        indexes = [models.Index(fields=["product", "created_at"])]

    def __str__(self) -> str:
        return f"{self.product} · {self.get_movement_type_display()} {self.quantity:+d}"


class ServiceConsumable(TenantScopedModel):
    """Insumo que gasta un servicio (regla 40). Es configuración: se borra físicamente."""

    service = models.ForeignKey("catalog.Service", on_delete=models.PROTECT, related_name="consumables")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="used_in")
    quantity = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["service", "product"],
                name="uq_serviceconsumable_service_product",
                violation_error_message="Ese producto ya es insumo del servicio.",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="ck_serviceconsumable_quantity_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.service} · {self.product} × {self.quantity}"
