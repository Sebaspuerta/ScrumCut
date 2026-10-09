import io
import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from PIL import Image

from apps.audit.models import AuditLog
from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context
from apps.inventory import selectors, services
from apps.inventory.models import MovementType, Product, ServiceConsumable, StockMovement
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db


def _product(actor, name="Cera mate", initial_stock=0, **data) -> Product:
    values = {
        "name": name,
        "product_type": "venta",
        "purchase_cost": Decimal("8000"),
        "sale_price": Decimal("15000"),
        **data,
    }
    return services.create_product(actor, values, initial_stock=initial_stock)


def _image(fmt: str, size=(400, 300)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 80, 40)).save(buffer, format=fmt)
    return SimpleUploadedFile(f"foto.{fmt.lower()}", buffer.getvalue())


def _service(name="Corte", **extra) -> Service:
    return Service.objects.create(name=name, price=Decimal("25000"), duration_minutes=30, **extra)


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)


@pytest.fixture
def admin(member, in_shop):
    return member(Role.ADMIN, in_shop)


# ── Productos (reglas 30, 31, 35) ────────────────────────────────────────────


def test_crear_con_stock_inicial_lo_registra_como_movimiento(owner):
    product = _product(owner, initial_stock=12)

    product.refresh_from_db()
    assert product.current_stock == 12
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
    product = _product(owner, name="Cera mate")
    with pytest.raises(ValidationError):
        _product(owner, name="CERA MATE")
    services.soft_delete_product(owner, product.public_id)
    assert _product(owner, name="Cera mate").pk != product.pk


@pytest.mark.parametrize(
    ("field", "value"),
    [("product_type", "regalo"), ("purchase_cost", Decimal("-1")), ("sale_price", Decimal("-1")), ("name", " ")],
)
def test_datos_invalidos_del_producto(owner, field, value):
    with pytest.raises(ValidationError):
        _product(owner, **{field: value})


def test_categoria_borrada_o_ajena_no_se_asigna(owner, member, other_shop):
    deleted = services.create_category(owner, name="Vieja")
    services.soft_delete_category(owner, deleted.public_id, delete_products=False)
    with pytest.raises(ValidationError):
        _product(owner, category=deleted.public_id)

    with tenant_context(other_shop.pk):
        foreign = services.create_category(member(Role.OWNER, other_shop), name="Ajena")
    with pytest.raises(ValidationError):
        _product(owner, category=foreign.public_id)


def test_un_producto_borrado_no_se_usa_pero_su_historial_queda(owner):
    product = _product(owner, initial_stock=3)
    services.soft_delete_product(owner, product.public_id)

    with pytest.raises(Product.DoesNotExist):
        selectors.get_product(owner, product.public_id)
    with pytest.raises(Product.DoesNotExist):
        services.update_product(owner, product.public_id, {"supplier": "Otro"})
    with pytest.raises(Product.DoesNotExist):
        services.register_entry(owner, product.public_id, 1, "Compra")
    assert StockMovement.objects.filter(product=product).count() == 1


def test_desactivar_y_activar(owner):
    product = _product(owner)
    services.deactivate_product(owner, product.public_id)
    assert list(selectors.list_products(owner)) == []
    assert list(selectors.list_products(owner, active_only=False)) == [product]
    services.activate_product(owner, product.public_id)
    assert list(selectors.list_products(owner)) == [product]


# ── Stock (reglas 32–34, defectos 14–16) ─────────────────────────────────────


def test_update_product_no_toca_el_stock(owner):
    product = _product(owner, initial_stock=5)
    with pytest.raises(TypeError):
        services.update_product(owner, product.public_id, {"current_stock": 99})
    services.update_product(owner, product.public_id, {"sale_price": Decimal("16000")})
    product.refresh_from_db()
    assert product.current_stock == 5
    assert product.sale_price == Decimal("16000")


def test_entrada_valida_y_su_movimiento(owner):
    product = _product(owner, initial_stock=2)
    movement = services.register_entry(owner, product.public_id, 10, "  Compra a proveedor  ", Decimal("7500"))

    product.refresh_from_db()
    assert product.current_stock == 12
    assert (movement.stock_before, movement.stock_after, movement.quantity) == (2, 12, 10)
    assert (movement.unit_cost, movement.reason, movement.created_by) == (
        Decimal("7500"),
        "Compra a proveedor",
        owner.user,
    )


@pytest.mark.parametrize(("quantity", "reason"), [(0, "Compra"), (-3, "Compra"), (5, "   ")])
def test_entrada_exige_cantidad_positiva_y_motivo(owner, quantity, reason):
    product = _product(owner)
    with pytest.raises(ValidationError):
        services.register_entry(owner, product.public_id, quantity, reason)
    assert product.movements.count() == 0


def test_ajuste_con_signo_y_nunca_negativo(owner):
    product = _product(owner, initial_stock=4)
    services.register_adjustment(owner, product.public_id, -3, "Conteo físico")
    with pytest.raises(ValidationError) as excinfo:
        services.register_adjustment(owner, product.public_id, -2, "Conteo físico")
    assert excinfo.value.error_list[0].code == "insufficient_stock"
    with pytest.raises(ValidationError):
        services.register_adjustment(owner, product.public_id, 0, "Nada")

    product.refresh_from_db()
    assert product.current_stock == 1
    assert product.movements.count() == 2


def test_la_base_rechaza_stock_negativo_aunque_alguien_salte_el_servicio(owner):
    product = _product(owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(current_stock=-1)


def test_un_movimiento_de_stock_no_se_edita_ni_se_borra(owner):
    movement = _product(owner, initial_stock=1).movements.get()
    movement.reason = "Cambiado"
    with pytest.raises(PermissionError):
        movement.save()
    with pytest.raises(PermissionError):
        movement.delete()
    with pytest.raises(PermissionError):
        StockMovement.objects.filter(pk=movement.pk).update(reason="x")
    with pytest.raises(PermissionError):
        StockMovement.objects.filter(pk=movement.pk).delete()


@pytest.mark.django_db(transaction=True)
def test_dos_salidas_simultaneas_no_venden_la_ultima_unidad_dos_veces(member, shop):
    """Defecto 14: con el bloqueo, la segunda salida espera y ve el stock ya descontado."""
    with tenant_context(shop.pk):
        owner = member(Role.OWNER, shop)
        product = _product(owner, initial_stock=1)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def sell() -> None:
        try:
            with tenant_context(shop.pk):
                barrier.wait()
                services.apply_stock_movement(product, -1, MovementType.SALE, "Venta", owner)
            outcomes.append("ok")
        except ValidationError:
            outcomes.append("sin_stock")
        finally:
            connection.close()

    threads = [threading.Thread(target=sell) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["ok", "sin_stock"]
    with tenant_context(shop.pk):
        product.refresh_from_db()
        assert product.current_stock == 0
        assert product.movements.filter(movement_type=MovementType.SALE).count() == 1


# ── Foto (regla 36) ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_la_foto_se_recorta_a_200_y_se_guarda_por_barberia(owner, settings, tmp_path, fmt):
    settings.MEDIA_ROOT = tmp_path
    product = _product(owner)
    services.upload_product_photo(owner, product.public_id, _image(fmt, size=(400, 300)))

    product.refresh_from_db()
    assert product.photo.name == f"barbershops/{owner.barbershop.public_id}/products/{product.public_id}.png"
    with Image.open(product.photo.path) as saved:
        assert (saved.format, saved.size) == ("PNG", (200, 200))


def test_cambiar_la_foto_reemplaza_el_archivo(owner, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    product = _product(owner)
    services.upload_product_photo(owner, product.public_id, _image("PNG"))
    services.upload_product_photo(owner, product.public_id, _image("JPEG"))
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
    product = _product(owner)
    with pytest.raises(ValidationError):
        services.upload_product_photo(owner, product.public_id, upload)


def test_un_gif_real_se_rechaza(owner, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    product = _product(owner)
    with pytest.raises(ValidationError):
        services.upload_product_photo(owner, product.public_id, _image("GIF"))


# ── Categorías (regla 37) ────────────────────────────────────────────────────


def test_borrar_categoria_deja_los_productos_sin_categoria(owner):
    category = services.create_category(owner, name="Cuidado")
    product = _product(owner, category=category.public_id)
    services.soft_delete_category(owner, category.public_id, delete_products=False)

    product.refresh_from_db()
    assert product.category is None
    assert not product.is_deleted
    assert AuditLog.objects.get(action="categoria_producto.eliminar").after["uncategorized_products"] == [
        str(product.public_id)
    ]


def test_borrar_categoria_con_sus_productos(owner):
    category = services.create_category(owner, name="Cuidado")
    product = _product(owner, category=category.public_id)
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
    product = _product(owner, name="Cuchilla", product_type="consumible")

    consumable = services.add_consumable(owner, service.public_id, product.public_id, 2)
    assert list(selectors.consumables_for(service)) == [consumable]
    with pytest.raises(ValidationError):
        services.add_consumable(owner, service.public_id, product.public_id, 1)

    services.update_consumable(owner, consumable.public_id, 3)
    consumable.refresh_from_db()
    assert consumable.quantity == 3

    services.remove_consumable(owner, consumable.public_id)
    assert not ServiceConsumable.objects.exists()
    assert AuditLog.objects.get(action="insumo.eliminar").before["quantity"] == 3


def test_insumo_con_cantidad_cero_o_inactivos_se_rechaza(owner):
    product = _product(owner, name="Cuchilla")
    with pytest.raises(ValidationError):
        services.add_consumable(owner, _service().public_id, product.public_id, 0)
    with pytest.raises(ValidationError):
        services.add_consumable(owner, _service("Barba", is_active=False).public_id, product.public_id, 1)
    services.deactivate_product(owner, product.public_id)
    with pytest.raises(ValidationError):
        services.add_consumable(owner, _service("Cejas").public_id, product.public_id, 1)


# ── Selectores ───────────────────────────────────────────────────────────────


def test_stock_bajo(owner):
    low = _product(owner, name="Bajo", initial_stock=2, minimum_stock=2)
    _product(owner, name="Suficiente", initial_stock=10, minimum_stock=2)
    _product(owner, name="Sin minimo", initial_stock=0)
    assert list(selectors.low_stock(owner)) == [low]


def test_por_vencer_incluye_vencidos_y_respeta_los_dias(owner):
    today = timezone.localdate()
    expired = _product(owner, name="Vencido", expiration_date=today - timedelta(days=1))
    soon = _product(owner, name="Pronto", expiration_date=today + timedelta(days=10))
    _product(owner, name="Lejano", expiration_date=today + timedelta(days=60))
    assert list(selectors.expiring(owner, days=30)) == [expired, soon]
    assert list(selectors.expiring(owner, days=5)) == [expired]


def test_filtros_de_la_lista(owner):
    category = services.create_category(owner, name="Cuidado")
    cera = _product(owner, name="Cera", category=category.public_id, supplier="Distribuidora Sur")
    cuchilla = _product(owner, name="Cuchilla", product_type="consumible")
    assert list(selectors.list_products(owner, category=category.public_id)) == [cera]
    assert list(selectors.list_products(owner, uncategorized=True)) == [cuchilla]
    assert list(selectors.list_products(owner, product_type="consumible")) == [cuchilla]
    assert list(selectors.list_products(owner, search="sur")) == [cera]


# ── Permisos y aislamiento ───────────────────────────────────────────────────


def test_el_administrador_gestiona_pero_no_elimina(admin):
    product = _product(admin, initial_stock=1)
    services.register_entry(admin, product.public_id, 2, "Compra")
    services.register_adjustment(admin, product.public_id, -1, "Conteo")
    category = services.create_category(admin, name="Cuidado")
    with pytest.raises(PermissionDenied):
        services.soft_delete_product(admin, product.public_id)
    with pytest.raises(PermissionDenied):
        services.soft_delete_category(admin, category.public_id, delete_products=False)


@pytest.mark.parametrize("role", [Role.BARBER, Role.CASHIER, Role.VIEWER])
def test_los_demas_roles_solo_ven(member, in_shop, owner, role):
    product = _product(owner, initial_stock=1)
    reader = member(role, in_shop)
    with pytest.raises(PermissionDenied):
        _product(reader, name="Otro")
    with pytest.raises(PermissionDenied):
        services.register_entry(reader, product.public_id, 1, "Compra")
    with pytest.raises(PermissionDenied):
        services.register_adjustment(reader, product.public_id, -1, "Conteo")
    with pytest.raises(PermissionDenied):
        services.add_consumable(reader, _service().public_id, product.public_id, 1)
    assert list(selectors.list_products(reader)) == [product]


def test_cada_barberia_ve_solo_su_inventario(member, shop, other_shop):
    with tenant_context(shop.pk):
        mine = _product(member(Role.OWNER, shop), name="Cera", initial_stock=5)
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        _product(theirs, name="Cera")
        assert [p.name for p in selectors.list_products(theirs)] == ["Cera"]
        with pytest.raises(Product.DoesNotExist):
            selectors.get_product(theirs, mine.public_id)
        with pytest.raises(Product.DoesNotExist):
            services.register_adjustment(theirs, mine.public_id, -5, "Robo")
    with tenant_context(shop.pk):
        mine.refresh_from_db()
        assert mine.current_stock == 5
