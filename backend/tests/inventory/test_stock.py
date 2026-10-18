"""Stock: entradas, ajustes y su historial (reglas 32–34, defectos 14–16)."""

import threading
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.core.tenant_context import tenant_context
from apps.inventory import services
from apps.inventory.models import MovementType, StockLevel, StockMovement
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role
from tests.concurrency import run_threads
from tests.conftest import scope_of, stock_of
from tests.inventory.helpers import make_product

pytestmark = pytest.mark.django_db


# ── Stock (reglas 32–34, defectos 14–16) ─────────────────────────────────────


def test_update_product_no_toca_el_stock(owner):
    product = make_product(owner, initial_stock=5)
    with pytest.raises(TypeError):
        services.update_product(owner, product.public_id, data={"current_stock": 99})
    services.update_product(owner, product.public_id, data={"sale_price": Decimal("16000")})
    product.refresh_from_db()
    assert stock_of(product) == 5
    assert product.sale_price == Decimal("16000")


def test_entrada_valida_y_su_movimiento(owner):
    product = make_product(owner, initial_stock=2)
    movement = services.register_entry(
        owner,
        product.public_id,
        quantity=10,
        reason="  Compra a proveedor  ",
        unit_cost=Decimal("7500"),
        scope=scope_of(owner),
    )

    assert stock_of(product) == 12
    assert (movement.stock_before, movement.stock_after, movement.quantity) == (2, 12, 10)
    assert (movement.unit_cost, movement.reason, movement.created_by) == (
        Decimal("7500"),
        "Compra a proveedor",
        owner.user,
    )


@pytest.mark.parametrize(("quantity", "reason"), [(0, "Compra"), (-3, "Compra"), (5, "   ")])
def test_entrada_exige_cantidad_positiva_y_motivo(owner, quantity, reason):
    product = make_product(owner)
    with pytest.raises(ValidationError):
        services.register_entry(owner, product.public_id, quantity=quantity, reason=reason, scope=scope_of(owner))
    assert product.movements.count() == 0


def test_ajuste_con_signo_y_nunca_negativo(owner):
    product = make_product(owner, initial_stock=4)
    services.register_adjustment(owner, product.public_id, quantity=-3, reason="Conteo físico", scope=scope_of(owner))
    with pytest.raises(ValidationError) as excinfo:
        services.register_adjustment(
            owner, product.public_id, quantity=-2, reason="Conteo físico", scope=scope_of(owner)
        )
    assert excinfo.value.error_list[0].code == "insufficient_stock"
    with pytest.raises(ValidationError):
        services.register_adjustment(owner, product.public_id, quantity=0, reason="Nada", scope=scope_of(owner))

    assert stock_of(product) == 1
    assert product.movements.count() == 2


def test_la_base_rechaza_stock_negativo_aunque_alguien_salte_el_servicio(owner):
    product = make_product(owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        StockLevel.objects.filter(product=product).update(quantity=-1)


def test_un_movimiento_de_stock_no_se_edita_ni_se_borra(owner):
    movement = make_product(owner, initial_stock=1).movements.get()
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
        product = make_product(owner, initial_stock=1)
        branch = Branch.objects.get()
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def sell() -> None:
        try:
            with tenant_context(shop.pk):
                barrier.wait()
                services.apply_stock_movement(
                    product, -1, branch=branch, movement_type=MovementType.SALE, reason="Venta", actor=owner
                )
            outcomes.append("ok")
        except ValidationError:
            outcomes.append("sin_stock")
        finally:
            connection.close()

    threads = [threading.Thread(target=sell) for _ in range(2)]
    run_threads(threads)

    assert sorted(outcomes) == ["ok", "sin_stock"]
    with tenant_context(shop.pk):
        assert stock_of(product) == 0
        assert product.movements.filter(movement_type=MovementType.SALE).count() == 1
