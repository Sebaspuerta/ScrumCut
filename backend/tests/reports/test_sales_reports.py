"""Reportes de ventas: días locales (defecto 28), valores copiados al cerrar (defectos 1 a 3) y sin N+1 (27)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cash import services as cash
from apps.inventory import services as inventory
from apps.reports.selectors import income, sales
from apps.sales.selectors import local_today
from apps.staff import services as staff
from tests.reports.helpers import close_at, sell

pytestmark = pytest.mark.django_db

D = Decimal


def test_las_ventas_se_agrupan_por_dia_local_de_bogota(world):
    w = world
    late = sell(w, w.ana, service=w.corte)
    morning = sell(w, w.beto, service=w.barba)
    close_at(late, datetime(2026, 10, 5, 23, 0))  # en UTC ya es el 6 de octubre
    close_at(morning, datetime(2026, 10, 6, 10, 0))

    rows = sales.sales_by_period(w.owner, date(2026, 10, 5), date(2026, 10, 6))

    assert [(row["day"], row["orders"], row["total"]) for row in rows] == [
        (date(2026, 10, 5), 1, D("25000")),
        (date(2026, 10, 6), 1, D("15000")),
    ]
    assert sales.sales_by_period(w.owner, date(2026, 10, 6), date(2026, 10, 6))[0]["total"] == D("15000")


def test_los_dias_sin_ventas_aparecen_en_cero(world):
    w = world
    close_at(sell(w, w.ana, service=w.corte), datetime(2026, 10, 5, 12, 0))
    close_at(sell(w, w.beto, service=w.barba), datetime(2026, 10, 7, 12, 0))

    rows = sales.sales_by_period(w.owner, date(2026, 10, 5), date(2026, 10, 7))

    assert [(row["day"], row["orders"], row["total"]) for row in rows] == [
        (date(2026, 10, 5), 1, D("25000")),
        (date(2026, 10, 6), 0, D("0")),
        (date(2026, 10, 7), 1, D("15000")),
    ]
    assert len(sales.sales_by_period(w.owner)) == 30


def test_cambiar_comision_y_costo_despues_de_cerrar_no_cambia_los_reportes(world):
    w = world
    sell(w, w.ana, service=w.corte)
    sell(w, w.ana, product=w.cera)
    before = (sales.sales_by_barber(w.owner), sales.top_products(w.owner), income.income_statement(w.owner))

    staff.set_commission(w.owner, w.ana.public_id, "percentage", 10)
    inventory.update_product(w.owner, w.cera.public_id, {"purchase_cost": D("1")})

    after = (sales.sales_by_barber(w.owner), sales.top_products(w.owner), income.income_statement(w.owner))
    assert after == before
    ana, cera, statement = after[0][0], after[1][0], after[2]
    assert (ana["services"], ana["sales"], ana["commission"]) == (1, D("25000"), D("10000"))  # la Cera no es de Ana
    assert (cera["quantity"], cera["sales"], cera["cost"]) == (1, D("20000"), D("8000"))
    assert (statement["product_cost"], statement["consumables_cost"], statement["commissions"]) == (
        D("8000"),
        D("1000"),
        D("10000"),
    )


def test_estado_de_resultados_con_descuento_y_gastos(world):
    w = world
    sell(w, w.ana, service=w.corte)
    sell(w, w.beto, product=w.cera)
    cash.register_manual_movement(w.cashier, w.session.public_id, "gasto", D("4000"), "efectivo", "Aseo")
    cash.register_manual_movement(w.cashier, w.session.public_id, "retiro", D("9000"), "efectivo", "Dueño")

    statement = income.income_statement(w.owner)

    assert statement == {
        "gross_sales": D("45000"),
        "discounts": D("0"),
        "net_sales": D("45000"),
        "product_cost": D("8000"),
        "consumables_cost": D("1000"),
        "commissions": D("10000"),
        "gross_profit": D("26000"),
        "expenses": D("4000"),  # el retiro no es gasto
        "operating_profit": D("22000"),
    }


def test_por_barbero_y_por_producto_sin_n_mas_1(world, django_assert_max_num_queries):
    w = world
    for _ in range(3):
        sell(w, w.ana, service=w.corte)
        sell(w, w.beto, service=w.barba)
        sell(w, w.beto, product=w.cera)
        sell(w, w.ana, product=w.cuchilla)
    w.owner.refresh_from_db()  # sin la barbería en caché: la consulta de la zona horaria cuenta

    with django_assert_max_num_queries(2):
        by_barber = sales.sales_by_barber(w.owner)
    with django_assert_max_num_queries(2):
        products = sales.top_products(w.owner)

    assert [(row["name"], row["services"]) for row in by_barber] == [("Ana", 3), ("Beto", 3)]
    assert [(row["name"], row["quantity"]) for row in products] == [("Cera", 3), ("Cuchilla", 3)]


def test_el_rango_por_defecto_son_los_ultimos_30_dias(world):
    w = world
    old = sell(w, w.ana, service=w.corte)
    sell(w, w.ana, service=w.corte)
    today = local_today(w.owner)
    close_at(old, datetime.combine(today - timedelta(days=30), time(12)))

    assert sum(row["orders"] for row in sales.sales_by_period(w.owner)) == 1
    with pytest.raises(ValidationError):
        sales.sales_by_period(w.owner, today, today - timedelta(days=1))
