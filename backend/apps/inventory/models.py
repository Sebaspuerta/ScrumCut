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
            models.CheckConstraint(condition=models.Q(purchase_cost__gte=0), name="ck_product_cost_not_negative"),
            models.CheckConstraint(condition=models.Q(sale_price__gte=0), name="ck_product_price_not_negative"),
            models.CheckConstraint(
                condition=models.Q(product_type__in=ProductType.values), name="ck_product_type_valid"
            ),
            # Destino de la llave compuesta de ProductBranchPrice (apps/core/tenant_keys.py).
            models.UniqueConstraint(fields=["barbershop", "id"], name="uq_product_barbershop_id"),
        ]

    def __str__(self) -> str:
        return self.name


class MovementType(models.TextChoices):
    ENTRY = "entrada", "Entrada"
    ADJUSTMENT = "ajuste", "Ajuste"
    SALE = "salida_venta", "Salida por venta"
    SERVICE = "salida_servicio", "Insumo de servicio"
    REVERSAL = "reversion", "Reversión"
    TRANSFER_OUT = "traslado_salida", "Traslado (salida)"
    TRANSFER_IN = "traslado_entrada", "Traslado (entrada)"


class StockMovement(AppendOnlyModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    # La existencia que se movió es la de esta sede (decisión 6 de docs/sedes.md).
    branch = models.ForeignKey("tenancy.Branch", on_delete=models.PROTECT, related_name="stock_movements")
    movement_type = models.CharField("tipo", max_length=16, choices=MovementType.choices)
    quantity = models.IntegerField("cantidad")  # con signo: + entra, − sale
    stock_before = models.IntegerField("stock antes")
    stock_after = models.IntegerField("stock después")
    unit_cost = models.DecimalField("costo unitario", **_MONEY)
    reason = models.TextField("motivo")
    # Origen del movimiento ("order:<public_id>"), para revertirlo exacto sin que inventario dependa de sales.
    reference = models.CharField("referencia", max_length=64, blank=True, db_index=True)
    # Las dos patas de un traslado entre sedes comparten este valor; nulo en todo lo demás.
    transfer_id = models.UUIDField("traslado", null=True, blank=True, db_index=True)
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
            models.CheckConstraint(
                condition=models.Q(transfer_id__isnull=True)
                | models.Q(movement_type__in=[MovementType.TRANSFER_OUT, MovementType.TRANSFER_IN]),
                name="ck_stockmovement_transfer_id_only_on_transfers",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "created_at"]),
            models.Index(fields=["barbershop", "branch", "created_at"], name="ix_stockmove_branch_created"),
        ]

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


class ProductBranchPrice(TenantScopedModel):
    """Precio de venta de un producto en una sede (decisión 17 de docs/sedes.md).

    Sin fila, rige `Product.sale_price`. Lo resuelve `apps.catalog.branch_prices.current_price`.
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="branch_prices")
    branch = models.ForeignKey("tenancy.Branch", on_delete=models.PROTECT, related_name="product_prices")
    price = models.DecimalField("precio en la sede", **_MONEY)

    class Meta:
        verbose_name = "precio de producto en la sede"
        constraints = [
            models.UniqueConstraint(fields=["product", "branch"], name="uq_productbranchprice_product_branch"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="ck_productbranchprice_not_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.product} · {self.branch} · {self.price}"


class StockLevel(TenantScopedModel):
    """Existencia de un producto en una sede (decisión 6 de docs/sedes.md).

    Solo la cambia `services.apply_stock_movement`. El total de la barbería es la suma por sede.
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_levels")
    branch = models.ForeignKey("tenancy.Branch", on_delete=models.PROTECT, related_name="stock_levels")
    quantity = models.IntegerField("existencia", default=0)

    class Meta:
        verbose_name = "existencia en la sede"
        constraints = [
            models.UniqueConstraint(fields=["product", "branch"], name="uq_stocklevel_product_branch"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="ck_stocklevel_not_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.product} · {self.branch} · {self.quantity}"
