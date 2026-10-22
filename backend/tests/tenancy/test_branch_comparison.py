"""Comparativo entre sedes (fase S5 de docs/sedes.md): cifras, Total, alcance, sedes inactivas y consultas.

`world` deja Centro con 5 ceras (costo 8 000) y 10 cuchillas (costo 1 000) y una caja con base
50 000; `norte`, 3 ceras y 4 cuchillas y una caja con base 0.
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.exceptions import PermissionDenied
from openpyxl import load_workbook

from apps.cash import services as cash
from apps.cash.models import MovementKind
from apps.inventory import selectors as inventory_selectors
from apps.inventory import services as inventory
from apps.receivables import services as receivables
from apps.receivables.models import Receivable
from apps.receivables.selectors import receivables_summary
from apps.reports.excel.builder import build_business_report
from apps.reports.selectors import cash as cash_reports
from apps.reports.selectors import income, sales
from apps.reports.selectors.branches import COUNT_METRICS, MONEY_METRICS, branch_comparison
from apps.sales import services as orders
from apps.staff.models import BarberBranch
from apps.tenancy.branch_scope import ALL, BranchScope
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role
from tests.conftest import scope_of
from tests.reports.helpers import sell

D = Decimal
SUMMED = MONEY_METRICS + COUNT_METRICS


def _day(world, norte) -> None:
    """Un día en las dos sedes.

    Centro: Ana corta (25 000, gasta 1 cuchilla) y Beto vende 1 cera (20 000), en efectivo.
    Gasto de 5 000. Traslado de 2 ceras a Norte. Cierre contando 89 000 frente a un esperado
    de 50 000 + 25 000 + 20 000 − 5 000 = 90 000: diferencia −1 000.
    Norte: Beto corta (25 000, gasta 1 cuchilla) y hace una barba fiada a Laura (15 000), que
    abona 5 000 en la caja de Norte.
    """
    in_norte = scope_of(world.owner, norte)
    sell(world, world.ana, service=world.corte)
    sell(world, world.beto, product=world.cera)
    cash.register_manual_movement(
        world.cashier,
        world.session.public_id,
        scope=scope_of(world.cashier),
        kind="gasto",
        amount=D("5000"),
        payment_method="efectivo",
        description="Toallas",
    )
    inventory.transfer_stock(
        world.owner,
        world.cera.public_id,
        scope=scope_of(world.owner, world.branch),
        destination=norte.public_id,
        quantity=2,
        reason="Reparto",
    )
    _close_centro(world)
    orders.quick_register(
        world.owner, in_norte, barber=world.beto.public_id, method="efectivo", service=world.corte.public_id
    )
    _credit_in_norte(world, in_norte)


def _close_centro(world) -> None:
    """Cuenta 89 000 frente a 90 000 esperados: con diferencia, la nota es obligatoria."""
    cash.close_session(
        world.cashier,
        world.session.public_id,
        scope=scope_of(world.cashier),
        counted_amount=D("89000"),
        notes="Vueltas mal entregadas",
    )


def _credit_in_norte(world, in_norte) -> None:
    order = orders.create_order(world.owner, in_norte, client=world.laura.public_id)
    orders.add_item(
        world.owner, order.public_id, service=world.barba.public_id, barber=world.beto.public_id, scope=in_norte
    )
    orders.close_order(world.owner, order.public_id, as_credit=True, scope=in_norte)
    debt = Receivable.objects.get(order=order)
    receivables.add_payment(world.owner, debt.public_id, scope=in_norte, amount=D("5000"), method="efectivo")


def _everything(world):
    return branch_comparison(world.owner, scope=scope_of(world.owner, everything=True))


def _by_name(comparison) -> dict:
    return {row["name"]: row for row in comparison["branches"]}


def _figures(row) -> dict:
    return {metric: row[metric] for metric in (*SUMMED, "ticket")}


CENTRO = {
    "orders": 2,
    "sales": D("45000"),
    "ticket": D("22500"),
    "services": D("25000"),
    "products": D("20000"),
    "expenses": D("5000"),
    "result": D("40000"),
    "receivables_pending": D("0"),
    "receivables_collected": D("0"),
    "closings": 1,
    "closing_differences": D("-1000"),
    "stock_value": D("25000"),  # 2 ceras × 8 000 + 9 cuchillas × 1 000
    "units_in": 0,
    "units_out": 2,
    "transfers_in": 0,
    "transfers_out": 1,
}
NORTE = {
    "orders": 2,
    "sales": D("40000"),
    "ticket": D("20000"),
    "services": D("40000"),
    "products": D("0"),
    "expenses": D("0"),
    "result": D("40000"),
    "receivables_pending": D("10000"),
    "receivables_collected": D("5000"),  # 15 000 fiado − 5 000 abonado
    "closings": 0,
    "closing_differences": D("0"),
    "stock_value": D("43000"),  # 5 ceras × 8 000 + 3 cuchillas × 1 000
    "units_in": 2,
    "units_out": 0,
    "transfers_in": 1,
    "transfers_out": 0,
}


def test_cada_cifra_de_centro_y_norte_cuadra_a_mano(world, norte):
    _day(world, norte)
    comparison = _everything(world)
    rows = _by_name(comparison)

    assert _figures(rows["Centro"]) == CENTRO
    assert _figures(rows["Norte"]) == NORTE
    total = comparison["total"]
    assert (total["sales"], total["orders"], total["ticket"]) == (D("85000"), 4, D("21250"))  # 85 000 / 4
    production = [(row["branch"], row["name"], row["orders"], row["total"]) for row in comparison["production"]["rows"]]
    # La cera de Centro se vendió sin barbero: no es producción de nadie.
    assert production == [("Centro", "Ana", 1, D("25000")), ("Norte", "Beto", 2, D("40000"))]
    assert comparison["production"]["total"] == {"orders": 3, "total": D("65000")}


def test_el_total_es_la_suma_de_las_sedes_en_cada_metrica(world, norte):
    _day(world, norte)
    comparison = _everything(world)

    for metric in SUMMED:
        assert comparison["total"][metric] == sum(row[metric] for row in comparison["branches"]), metric


def test_en_todas_el_total_coincide_con_los_reportes_sin_sede(world, norte):
    _day(world, norte)
    owner, everything = world.owner, scope_of(world.owner, everything=True)
    total = _everything(world)["total"]
    days = sales.sales_by_period(owner, scope=everything)
    mix = sales.income_mix(owner, scope=everything)
    closings = list(cash_reports.cash_closings(owner, scope=everything))
    movements = cash_reports.cash_movements(owner, scope=everything)
    levels = inventory_selectors.stock_levels(owner, scope=everything)

    assert (total["orders"], total["sales"]) == (sum(d["orders"] for d in days), sum(d["total"] for d in days))
    assert (total["services"], total["products"]) == (mix["services"]["amount"], mix["products"]["amount"])
    assert total["expenses"] == income.income_statement(owner, scope=everything)["expenses"]
    assert total["receivables_pending"] == receivables_summary(owner, scope=everything)["pending_balance"]
    paid = sum(m["amount"] for m in movements if m["kind"] == MovementKind.RECEIVABLE_PAYMENT)
    assert total["receivables_collected"] == paid
    assert (total["closings"], total["closing_differences"]) == (len(closings), sum(c["difference"] for c in closings))
    assert total["stock_value"] == sum(level.quantity * level.product.purchase_cost for level in levels)
    barbers = sales.sales_by_barber(owner, scope=everything)
    assert _everything(world)["production"]["total"]["total"] == sum(b["sales"] for b in barbers)


def test_una_comanda_con_dos_barberos_reparte_el_dinero_por_linea(world):
    """Corte de 25 000 de Ana y barba de 15 000 de Beto en la misma comanda: 1 comanda para cada
    uno, y cada uno suma solo su línea (25 000 y 15 000), nunca el total de 40 000."""
    centro = scope_of(world.owner, world.branch)
    order = orders.create_order(world.owner, centro, client=world.laura.public_id)
    for service, barber in ((world.corte, world.ana), (world.barba, world.beto)):
        orders.add_item(world.owner, order.public_id, service=service.public_id, barber=barber.public_id, scope=centro)
    orders.close_order(world.owner, order.public_id, as_credit=True, scope=centro)

    comparison = branch_comparison(world.owner, scope=centro)
    production = {row["name"]: (row["orders"], row["total"]) for row in comparison["production"]["rows"]}

    assert production == {"Ana": (1, D("25000")), "Beto": (1, D("15000"))}
    services = comparison["total"]["services"]
    assert services == D("40000")
    assert comparison["production"]["total"]["total"] <= services


# ── Alcance ──────────────────────────────────────────────────────────────────


def test_el_cajero_de_centro_solo_ve_centro(world, norte):
    _day(world, norte)
    comparison = branch_comparison(world.cashier, scope=scope_of(world.cashier))

    assert [row["name"] for row in comparison["branches"]] == ["Centro"]
    assert _figures(comparison["total"]) == CENTRO
    assert {row["branch"] for row in comparison["production"]["rows"]} == {"Centro"}


def test_todas_exige_ver_todas_las_sedes(world, member, in_shop):
    forged = BranchScope(world.cashier.pk, ALL, None, frozenset({world.branch.pk}))
    with pytest.raises(PermissionDenied):
        branch_comparison(world.cashier, scope=forged)
    barber = world.ana_login
    with pytest.raises(PermissionDenied):
        branch_comparison(barber, scope=scope_of(barber))
    viewer = member(Role.VIEWER, in_shop)
    assert branch_comparison(viewer, scope=scope_of(viewer, everything=True))["total"]["name"] == "Total"


def _cells(book, title: str) -> list[tuple]:
    return list(book[title].iter_rows(min_row=5, values_only=True))


def _branches_in(book, title: str) -> set[str]:
    """Los valores de la columna "Sede" de una hoja de detalle (el encabezado está en la fila 4)."""
    header = next(book[title].iter_rows(min_row=4, max_row=4, values_only=True))
    column = header.index("Sede")
    return {row[column] for row in _cells(book, title)}


def test_el_excel_de_centro_no_trae_datos_de_norte(world, norte):
    _day(world, norte)
    report = build_business_report(world.owner, scope=scope_of(world.owner, world.branch))
    book = load_workbook(BytesIO(report))

    summary = _cells(book, "Resumen por sede")
    assert [row[0] for row in summary[:2]] == ["Centro", "Total"]
    assert summary[0][2:4] == (2, 45000)  # comandas y ventas netas, como número
    assert book["Resumen por sede"]["D5"].number_format == "#,##0"
    assert "Norte" not in {cell for row in summary for cell in row}
    for title in ("Ventas", "Comisiones", "Movimientos de caja", "Cierres de caja"):
        assert _branches_in(book, title) <= {"Centro"}, title


def test_el_cajero_no_descarga_el_excel(world):
    with pytest.raises(PermissionDenied):
        build_business_report(world.cashier, scope=scope_of(world.cashier))


def test_en_todas_el_excel_tiene_cada_sede_y_su_columna(world, norte):
    _day(world, norte)
    book = load_workbook(BytesIO(build_business_report(world.owner, scope=scope_of(world.owner, everything=True))))

    summary = _cells(book, "Resumen por sede")
    assert [row[0] for row in summary[:3]] == ["Centro", "Norte", "Total"]
    assert summary[2][3] == 85000
    assert _branches_in(book, "Ventas") == {"Centro", "Norte"}
    assert _branches_in(book, "Fiados") == {"Norte"}


# ── Sedes inactivas y período vacío ──────────────────────────────────────────


def test_una_sede_inactiva_sale_solo_si_tuvo_movimiento_y_marcada(world, norte):
    _day(world, norte)
    Branch.objects.create(name="Sur", is_active=False)
    Branch.objects.filter(pk=norte.pk).update(is_active=False)

    rows = _by_name(_everything(world))

    assert set(rows) == {"Centro", "Norte"}
    assert (rows["Centro"]["is_active"], rows["Norte"]["is_active"]) == (True, False)


def test_un_periodo_sin_movimiento_da_ceros(world, norte):
    comparison = branch_comparison(
        world.owner, date(2025, 1, 1), date(2025, 1, 31), scope=scope_of(world.owner, everything=True)
    )

    period_metrics = [metric for metric in SUMMED if metric not in ("receivables_pending", "stock_value")]
    assert [row["name"] for row in comparison["branches"]] == ["Centro", "Norte"]
    assert all(not comparison["total"][metric] for metric in period_metrics)
    assert comparison["total"]["ticket"] == 0
    assert comparison["production"] == {"rows": [], "total": {"orders": 0, "total": D("0")}}
    assert comparison["total"]["stock_value"] == D("78000")  # el de hoy: 50 000 en Centro y 28 000 en Norte


# ── Rendimiento ──────────────────────────────────────────────────────────────

# Una por grupo: sedes, comandas, líneas, caja, cierres, fiados, stock, traslados y producción.
COMPARISON_QUERIES = 9


def _more_branches(world, count: int) -> None:
    """Sedes extra con una venta y un gasto cada una."""
    for number in range(count):
        branch = Branch.objects.create(name=f"Sede {number}")
        BarberBranch.objects.create(barber=world.beto, branch=branch)
        inventory.register_entry(
            world.owner, world.cuchilla.public_id, scope=scope_of(world.owner, branch), quantity=2, reason="Compra"
        )
        session = cash.open_session(world.owner, scope_of(world.owner, branch), opening_amount=D("0"))
        orders.quick_register(
            world.owner,
            scope_of(world.owner, branch),
            barber=world.beto.public_id,
            method="efectivo",
            service=world.corte.public_id,
        )
        cash.register_manual_movement(
            world.owner,
            session.public_id,
            scope=scope_of(world.owner, branch),
            kind="gasto",
            amount=D("1000"),
            payment_method="efectivo",
            description="Aseo",
        )


@pytest.mark.parametrize("extra_branches", [0, 2])
def test_las_consultas_no_dependen_del_numero_de_sedes(world, django_assert_num_queries, extra_branches):
    sell(world, world.ana, service=world.corte)
    _more_branches(world, extra_branches)
    everything = scope_of(world.owner, everything=True)

    with django_assert_num_queries(COMPARISON_QUERIES):
        comparison = branch_comparison(world.owner, scope=everything)

    assert len(comparison["branches"]) == 1 + extra_branches
