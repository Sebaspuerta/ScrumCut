"""Stock por sede (fase S4b de docs/sedes.md): traslados, consumo, alertas y aislamiento.

`world` deja 5 ceras y 10 cuchillas en Centro; `norte`, 3 ceras y 4 cuchillas en Norte.
"""

import threading
from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction

from apps.alerts import selectors as alert_selectors
from apps.alerts import services as alerts
from apps.alerts.models import Alert, AlertType
from apps.audit.models import AuditLog
from apps.core.tenant_context import tenant_context
from apps.inventory import selectors, services
from apps.inventory.models import MovementType, StockMovement
from apps.sales import services as sales
from apps.tenancy.branch_scope import resolve_scope
from apps.tenancy.models import Branch
from tests.alerts.helpers import TODAY
from tests.concurrency import run_threads
from tests.conftest import scope_of, stock_of

TRANSFERS = (MovementType.TRANSFER_OUT, MovementType.TRANSFER_IN)


def _transfer(world, origin, destination, quantity, product=None):
    return services.transfer_stock(
        world.owner,
        (product or world.cera).public_id,
        scope=scope_of(world.owner, origin),
        destination=destination.public_id,
        quantity=quantity,
        reason="Reparto",
    )


def _cera_by_branch(world, norte) -> tuple[int, int]:
    return stock_of(world.cera, world.branch), stock_of(world.cera, norte)


# ── Traslados ────────────────────────────────────────────────────────────────


def test_un_traslado_mueve_las_unidades_y_enlaza_sus_dos_movimientos(world, norte):
    out, into = _transfer(world, world.branch, norte, 2)

    assert _cera_by_branch(world, norte) == (3, 5)
    assert (out.movement_type, out.branch, out.quantity) == (MovementType.TRANSFER_OUT, world.branch, -2)
    assert (into.movement_type, into.branch, into.quantity) == (MovementType.TRANSFER_IN, norte, 2)
    assert out.transfer_id is not None and out.transfer_id == into.transfer_id
    log = AuditLog.objects.get(action="inventario.trasladar")
    assert (log.branch, log.after["transfer_id"], log.after["quantity"]) == (world.branch, str(out.transfer_id), 2)


def test_un_traslado_se_lee_por_su_transfer_id_con_sus_dos_movimientos(world, norte):
    _transfer(world, norte, world.branch, 1)  # otro traslado, que no debe aparecer
    out, _ = _transfer(world, world.branch, norte, 2)

    legs = StockMovement.objects.filter(transfer_id=out.transfer_id).order_by("quantity")

    assert [(leg.branch, leg.quantity) for leg in legs] == [(world.branch, -2), (norte, 2)]
    assert sum(leg.quantity for leg in legs) == 0


def test_la_base_solo_acepta_transfer_id_en_un_traslado(world):
    entry = StockMovement.objects.filter(product=world.cera).get()
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO inventory_stockmovement (public_id, created_at, updated_at, barbershop_id, product_id, "
            "branch_id, movement_type, quantity, stock_before, stock_after, unit_cost, reason, reference, "
            "transfer_id, created_by_id) VALUES (gen_random_uuid(), now(), now(), %s, %s, %s, 'entrada', 1, 0, 1, "
            "0, 'x', '', gen_random_uuid(), %s)",
            [entry.barbershop_id, entry.product_id, entry.branch_id, entry.created_by_id],
        )


@pytest.mark.parametrize("quantity", [0, -1])
def test_un_traslado_sin_unidades_se_rechaza(world, norte, quantity):
    with pytest.raises(ValidationError):
        _transfer(world, world.branch, norte, quantity)
    assert not StockMovement.objects.filter(movement_type__in=TRANSFERS).exists()


def test_un_traslado_a_la_misma_sede_se_rechaza(world, norte):
    with pytest.raises(ValidationError, match="distinta"):
        _transfer(world, world.branch, world.branch, 1)
    assert _cera_by_branch(world, norte) == (5, 3)


def test_un_traslado_a_una_sede_inactiva_se_rechaza(world, norte):
    Branch.objects.filter(pk=norte.pk).update(is_active=False)
    with pytest.raises(ValidationError):
        _transfer(world, world.branch, norte, 1)
    assert stock_of(world.cera, world.branch) == 5


def test_un_traslado_a_una_sede_de_otra_barberia_se_rechaza(world, make_shop):
    other = make_shop("b")
    with tenant_context(other.pk):
        foreign = Branch.objects.get()
    with pytest.raises(ValidationError):
        _transfer(world, world.branch, foreign, 1)
    assert stock_of(world.cera, world.branch) == 5


def test_un_traslado_no_deja_el_origen_en_negativo_ni_crea_nada(world, norte):
    with pytest.raises(ValidationError) as excinfo:
        _transfer(world, world.branch, norte, 6)
    assert excinfo.value.error_list[0].code == "insufficient_stock"
    assert _cera_by_branch(world, norte) == (5, 3)
    assert not StockMovement.objects.filter(movement_type__in=TRANSFERS).exists()


def test_en_todas_las_sedes_no_se_traslada(world, norte):
    with pytest.raises(ValidationError):
        services.transfer_stock(
            world.owner,
            world.cera.public_id,
            scope=scope_of(world.owner, everything=True),
            destination=norte.public_id,
            quantity=1,
            reason="Reparto",
        )


def _run_together(world, jobs) -> list[str]:
    """Corre cada traslado en su hilo, a la vez; devuelve "ok" o el código de cada rechazo."""
    barrier = threading.Barrier(len(jobs))
    outcomes: list[str] = []

    def run(job) -> None:
        try:
            with tenant_context(world.shop.pk):
                barrier.wait()
                job()
            outcomes.append("ok")
        except ValidationError as error:
            outcomes.append(error.error_list[0].code)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(job,)) for job in jobs]
    run_threads(threads)
    return sorted(outcomes)


def _job(world, scope, destination, quantity):
    return lambda: services.transfer_stock(
        world.owner,
        world.cera.public_id,
        scope=scope,
        destination=destination.public_id,
        quantity=quantity,
        reason="Reparto",
    )


@pytest.mark.django_db(transaction=True)
def test_dos_traslados_simultaneos_del_mismo_stock_no_lo_dejan_negativo(world, norte):
    centro = scope_of(world.owner, world.branch)
    jobs = [_job(world, centro, norte, 4), _job(world, centro, norte, 4)]

    assert _run_together(world, jobs) == ["insufficient_stock", "ok"]
    with tenant_context(world.shop.pk):
        assert _cera_by_branch(world, norte) == (1, 7)


@pytest.mark.django_db(transaction=True)
def test_dos_traslados_cruzados_simultaneos_no_se_bloquean_mutuamente(world, norte):
    """Los dos bloquean las mismas dos existencias en el mismo orden: no hay interbloqueo."""
    jobs = [
        _job(world, scope_of(world.owner, world.branch), norte, 2),
        _job(world, scope_of(world.owner, norte), world.branch, 1),
    ]

    assert _run_together(world, jobs) == ["ok", "ok"]
    with tenant_context(world.shop.pk):
        assert _cera_by_branch(world, norte) == (4, 4)


# ── Consumo de la comanda ────────────────────────────────────────────────────


def test_cerrar_una_comanda_gasta_el_stock_de_su_sede(world, norte):
    in_norte = scope_of(world.owner, norte)
    order = sales.create_order(world.owner, in_norte, client=world.laura.public_id)
    for item in ({"service": world.corte.public_id}, {"product": world.cera.public_id}):
        sales.add_item(world.owner, order.public_id, barber=world.ana.public_id, scope=in_norte, **item)
    sales.close_order(world.owner, order.public_id, as_credit=True, scope=in_norte)

    assert _cera_by_branch(world, norte) == (5, 2)
    assert (stock_of(world.cuchilla, world.branch), stock_of(world.cuchilla, norte)) == (10, 3)


# ── Alertas ──────────────────────────────────────────────────────────────────


def _open_alerts(alert_type) -> list[tuple]:
    alerts_open = Alert.objects.filter(alert_type=alert_type, resolved_at__isnull=True)
    return list(alerts_open.values_list("product__name", "branch__name"))


def test_el_stock_bajo_se_alerta_solo_en_la_sede_que_lo_tiene(world, norte):
    services.update_product(world.owner, world.cera.public_id, data={"minimum_stock": 4})
    alerts.generate_alerts(TODAY)

    assert _open_alerts(AlertType.LOW_STOCK) == [("Cera", "Norte")]


def test_por_vencer_solo_se_alerta_donde_hay_unidades(world, norte):
    services.update_product(world.owner, world.cera.public_id, data={"expiration_date": TODAY + timedelta(days=5)})
    services.register_adjustment(
        world.owner, world.cera.public_id, scope=scope_of(world.owner, norte), quantity=-3, reason="Conteo"
    )
    alerts.generate_alerts(TODAY)

    assert _open_alerts(AlertType.EXPIRING) == [("Cera", "Centro")]


def test_las_alertas_se_leen_por_el_alcance(world, norte):
    services.update_product(world.owner, world.cera.public_id, data={"minimum_stock": 4})
    alerts.generate_alerts(TODAY)

    def branches_seen(membership, scope):
        return {alert.branch for alert in alert_selectors.list_alerts(membership, scope=scope)}

    assert branches_seen(world.cashier, scope_of(world.cashier)) == set()
    assert branches_seen(world.owner, scope_of(world.owner, everything=True)) == {norte}


# ── Aislamiento ──────────────────────────────────────────────────────────────


def test_el_cajero_de_centro_no_ve_ni_mueve_el_stock_de_norte(world, norte):
    cashier = world.cashier
    scope = resolve_scope(cashier, str(norte.public_id))  # pedir Norte lo deja en Centro

    assert scope.branch == world.branch
    assert {level.branch for level in selectors.stock_levels(cashier, scope=scope)} == {world.branch}
    cera = selectors.get_product(cashier, world.cera.public_id, scope=scope)
    assert cera.stock == 5
    with pytest.raises(PermissionDenied):
        services.transfer_stock(
            cashier, world.cera.public_id, scope=scope, destination=norte.public_id, quantity=1, reason="Reparto"
        )
    assert stock_of(world.cera, norte) == 3


def test_en_todas_las_sedes_se_ve_cada_sede_con_el_total(world, norte):
    everything = scope_of(world.owner, everything=True)
    levels = selectors.stock_levels(world.owner, scope=everything)
    cera = {level.branch.name: (level.quantity, level.product_total) for level in levels if level.product == world.cera}

    assert cera == {"Centro": (5, 8), "Norte": (3, 8)}
    assert selectors.get_product(world.owner, world.cera.public_id, scope=everything).stock == 8
