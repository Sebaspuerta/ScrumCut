import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.audit.models import AuditLog
from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context
from apps.inventory import selectors, services
from apps.inventory.models import MovementType, Product, ServiceConsumable, StockMovement
from apps.tenancy.roles import Role
from tests.conftest import scope_of, stock_of
from tests.inventory.helpers import make_product

pytestmark = pytest.mark.django_db


def _image(fmt: str, size=(400, 300)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 80, 40)).save(buffer, format=fmt)
    return SimpleUploadedFile(f"foto.{fmt.lower()}", buffer.getvalue())


def _service(name="Corte", **extra) -> Service:
    return Service.objects.create(name=name, price=Decimal("25000"), duration_minutes=30, **extra)


@pytest.fixture
def admin(member, in_shop):
    return member(Role.ADMIN, in_shop)


# ── Productos (reglas 30, 31, 35) ────────────────────────────────────────────


def test_crear_con_stock_inicial_lo_registra_como_movimiento(owner):
    product = make_product(owner, initial_stock=12)

    assert stock_of(product) == 12
    movement = product.movements.get()
    assert (movement.movement_type, movement.quantity, movement.stock_before, movement.stock_after) == (
        MovementType.ENTRY,
        12,
        0,
        12,
    )
    assert movement.reason == "Inventario inicial"
    assert movement.unit_cost == Decimal("8000")


def test_nombre_unico_sin_mayusculas_y_el_borrado_lo_libera(owner):
    product = make_product(owner, name="Cera mate")
    with pytest.raises(ValidationError):
        make_product(owner, name="CERA MATE")
    services.soft_delete_product(owner, product.public_id)
    assert make_product(owner, name="Cera mate").pk != product.pk


@pytest.mark.parametrize(
    ("field", "value"),
    [("product_type", "regalo"), ("purchase_cost", Decimal("-1")), ("sale_price", Decimal("-1")), ("name", " ")],
)
def test_datos_invalidos_del_producto(owner, field, value):
    with pytest.raises(ValidationError):
        make_product(owner, **{field: value})


def test_categoria_borrada_o_ajena_no_se_asigna(owner, member, other_shop):
    deleted = services.create_category(owner, name="Vieja")
    services.soft_delete_category(owner, deleted.public_id, delete_products=False)
    with pytest.raises(ValidationError):
        make_product(owner, category=deleted.public_id)

    with tenant_context(other_shop.pk):
        foreign = services.create_category(member(Role.OWNER, other_shop), name="Ajena")
    with pytest.raises(ValidationError):
        make_product(owner, category=foreign.public_id)


def test_un_producto_borrado_no_se_usa_pero_su_historial_queda(owner):
    product = make_product(owner, initial_stock=3)
    services.soft_delete_product(owner, product.public_id)

    with pytest.raises(Product.DoesNotExist):
        selectors.get_product(owner, product.public_id, scope=scope_of(owner))
    with pytest.raises(Product.DoesNotExist):
        services.update_product(owner, product.public_id, data={"supplier": "Otro"})
    with pytest.raises(Product.DoesNotExist):
        services.register_entry(owner, product.public_id, quantity=1, reason="Compra", scope=scope_of(owner))
    assert StockMovement.objects.filter(product=product).count() == 1


def test_desactivar_y_activar(owner):
    product = make_product(owner)
    services.deactivate_product(owner, product.public_id)
    assert list(selectors.list_products(owner, scope=scope_of(owner))) == []
    assert list(selectors.list_products(owner, active_only=False, scope=scope_of(owner))) == [product]
    services.activate_product(owner, product.public_id)
    assert list(selectors.list_products(owner, scope=scope_of(owner))) == [product]


# ── Foto (regla 36) ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_la_foto_se_recorta_a_200_y_se_guarda_por_barberia(owner, settings, tmp_path, fmt):
    settings.MEDIA_ROOT = tmp_path
    product = make_product(owner)
    services.upload_product_photo(owner, product.public_id, upload=_image(fmt, size=(400, 300)))

    product.refresh_from_db()
    assert product.photo.name == f"barbershops/{owner.barbershop.public_id}/products/{product.public_id}.png"
    with Image.open(product.photo.path) as saved:
        assert (saved.format, saved.size) == ("PNG", (200, 200))


def test_cambiar_la_foto_reemplaza_el_archivo(owner, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    product = make_product(owner)
    services.upload_product_photo(owner, product.public_id, upload=_image("PNG"))
    services.upload_product_photo(owner, product.public_id, upload=_image("JPEG"))
    product.refresh_from_db()
    assert product.photo.name.endswith(f"{product.public_id}.png")
    assert len(list(tmp_path.rglob("*.png"))) == 1


@pytest.mark.parametrize(
    "upload",
    [
        SimpleUploadedFile("foto.png", b"esto no es una imagen"),
        SimpleUploadedFile("foto.png", b""),
        SimpleUploadedFile("foto.png", b"\x89PNG" + b"\x00" * (5 * 1024 * 1024)),
    ],
    ids=["texto_con_extension_png", "vacio", "mas_de_5_mb"],
)
def test_fotos_rechazadas(owner, settings, tmp_path, upload):
    settings.MEDIA_ROOT = tmp_path
    product = make_product(owner)
    with pytest.raises(ValidationError):
        services.upload_product_photo(owner, product.public_id, upload=upload)


def test_un_gif_real_se_rechaza(owner, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    product = make_product(owner)
    with pytest.raises(ValidationError):
        services.upload_product_photo(owner, product.public_id, upload=_image("GIF"))


# ── Categorías (regla 37) ────────────────────────────────────────────────────


def test_borrar_categoria_deja_los_productos_sin_categoria(owner):
    category = services.create_category(owner, name="Cuidado")
    product = make_product(owner, category=category.public_id)
    services.soft_delete_category(owner, category.public_id, delete_products=False)

    product.refresh_from_db()
    assert product.category is None
    assert not product.is_deleted
    assert AuditLog.objects.get(action="categoria_producto.eliminar").after["uncategorized_products"] == [
        str(product.public_id)
    ]


def test_borrar_categoria_con_sus_productos(owner):
    category = services.create_category(owner, name="Cuidado")
    product = make_product(owner, category=category.public_id)
    services.soft_delete_category(owner, category.public_id, delete_products=True)

    product.refresh_from_db()
    assert product.is_deleted
    assert AuditLog.objects.filter(action="producto.eliminar").count() == 1


def test_borrar_categoria_exige_elegir_que_pasa_con_los_productos(owner):
    category = services.create_category(owner, name="Cuidado")
    with pytest.raises(TypeError):
        services.soft_delete_category(owner, category.public_id)


# ── Insumos de servicios (regla 40) ──────────────────────────────────────────


def test_insumos_crear_editar_quitar(owner):
    service = _service()
    product = make_product(owner, name="Cuchilla", product_type="consumible")

    consumable = services.add_consumable(owner, service.public_id, product=product.public_id, quantity=2)
    assert list(selectors.consumables_for(service)) == [consumable]
    with pytest.raises(ValidationError):
        services.add_consumable(owner, service.public_id, product=product.public_id, quantity=1)

    services.update_consumable(owner, consumable.public_id, quantity=3)
    consumable.refresh_from_db()
    assert consumable.quantity == 3

    services.remove_consumable(owner, consumable.public_id)
    assert not ServiceConsumable.objects.exists()
    assert AuditLog.objects.get(action="insumo.eliminar").before["quantity"] == 3


def test_insumo_con_cantidad_cero_o_inactivos_se_rechaza(owner):
    product = make_product(owner, name="Cuchilla")
    with pytest.raises(ValidationError):
        services.add_consumable(owner, _service().public_id, product=product.public_id, quantity=0)
    with pytest.raises(ValidationError):
        services.add_consumable(
            owner, _service("Barba", is_active=False).public_id, product=product.public_id, quantity=1
        )
    services.deactivate_product(owner, product.public_id)
    with pytest.raises(ValidationError):
        services.add_consumable(owner, _service("Cejas").public_id, product=product.public_id, quantity=1)


# ── Selectores ───────────────────────────────────────────────────────────────


def test_stock_bajo(owner):
    low = make_product(owner, name="Bajo", initial_stock=2, minimum_stock=2)
    make_product(owner, name="Suficiente", initial_stock=10, minimum_stock=2)
    make_product(owner, name="Sin minimo", initial_stock=0)
    assert [level.product for level in selectors.low_stock(owner, scope=scope_of(owner))] == [low]


def test_por_vencer_incluye_vencidos_y_respeta_los_dias(owner):
    today = timezone.localdate()
    expired = make_product(owner, name="Vencido", initial_stock=1, expiration_date=today - timedelta(days=1))
    soon = make_product(owner, name="Pronto", initial_stock=1, expiration_date=today + timedelta(days=10))
    make_product(owner, name="Lejano", initial_stock=1, expiration_date=today + timedelta(days=60))
    make_product(owner, name="Sin unidades", expiration_date=today)

    def expiring_products(days):
        return [level.product for level in selectors.expiring(owner, days=days, scope=scope_of(owner))]

    assert expiring_products(30) == [expired, soon]
    assert expiring_products(5) == [expired]


def test_filtros_de_la_lista(owner):
    category = services.create_category(owner, name="Cuidado")
    cera = make_product(owner, name="Cera", category=category.public_id, supplier="Distribuidora Sur")
    cuchilla = make_product(owner, name="Cuchilla", product_type="consumible")
    assert list(selectors.list_products(owner, category=category.public_id, scope=scope_of(owner))) == [cera]
    assert list(selectors.list_products(owner, uncategorized=True, scope=scope_of(owner))) == [cuchilla]
    assert list(selectors.list_products(owner, product_type="consumible", scope=scope_of(owner))) == [cuchilla]
    assert list(selectors.list_products(owner, search="sur", scope=scope_of(owner))) == [cera]


# ── Permisos y aislamiento ───────────────────────────────────────────────────


def test_el_administrador_gestiona_pero_no_elimina(admin):
    product = make_product(admin, initial_stock=1)
    services.register_entry(admin, product.public_id, quantity=2, reason="Compra", scope=scope_of(admin))
    services.register_adjustment(admin, product.public_id, quantity=-1, reason="Conteo", scope=scope_of(admin))
    category = services.create_category(admin, name="Cuidado")
    with pytest.raises(PermissionDenied):
        services.soft_delete_product(admin, product.public_id)
    with pytest.raises(PermissionDenied):
        services.soft_delete_category(admin, category.public_id, delete_products=False)


@pytest.mark.parametrize("role", [Role.BARBER, Role.CASHIER, Role.VIEWER])
def test_los_demas_roles_solo_ven(member, in_shop, owner, role):
    product = make_product(owner, initial_stock=1)
    reader = member(role, in_shop)
    with pytest.raises(PermissionDenied):
        make_product(reader, name="Otro")
    with pytest.raises(PermissionDenied):
        services.register_entry(reader, product.public_id, quantity=1, reason="Compra", scope=scope_of(reader))
    with pytest.raises(PermissionDenied):
        services.register_adjustment(reader, product.public_id, quantity=-1, reason="Conteo", scope=scope_of(reader))
    with pytest.raises(PermissionDenied):
        services.add_consumable(reader, _service().public_id, product=product.public_id, quantity=1)
    assert list(selectors.list_products(reader, scope=scope_of(reader))) == [product]


def test_cada_barberia_ve_solo_su_inventario(member, shop, other_shop):
    with tenant_context(shop.pk):
        mine = make_product(member(Role.OWNER, shop), name="Cera", initial_stock=5)
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        make_product(theirs, name="Cera")
        assert [p.name for p in selectors.list_products(theirs, scope=scope_of(theirs))] == ["Cera"]
        with pytest.raises(Product.DoesNotExist):
            selectors.get_product(theirs, mine.public_id, scope=scope_of(theirs))
        with pytest.raises(Product.DoesNotExist):
            services.register_adjustment(theirs, mine.public_id, quantity=-5, reason="Robo", scope=scope_of(theirs))
    with tenant_context(shop.pk):
        assert stock_of(mine) == 5
