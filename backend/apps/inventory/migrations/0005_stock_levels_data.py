"""Paso 2 de 3 del stock por sede: el stock de cada producto pasa a la Sede principal de su barbería.

La Sede principal es la más antigua (menor id). Cada producto queda con una existencia en ella
igual a su `current_stock`, y los movimientos que ya existían quedan con esa sede.

La reversa vuelve a sumar en `current_stock` las existencias de todas las sedes. Qué se pierde:
en qué sede estaba cada unidad, y los movimientos quedan sin sede.
"""

from django.db import migrations
from django.db.models import IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from apps.core.tenant_keys import each_barbershop


def forwards(apps, schema_editor):
    Branch = apps.get_model("tenancy", "Branch")
    Product = apps.get_model("inventory", "Product")
    StockLevel = apps.get_model("inventory", "StockLevel")
    StockMovement = apps.get_model("inventory", "StockMovement")
    for barbershop_id in each_barbershop(apps, schema_editor):
        main = Branch.objects.filter(barbershop_id=barbershop_id).order_by("pk").first()
        if main is None:
            continue
        stocks = Product.objects.filter(barbershop_id=barbershop_id).values_list("pk", "current_stock")
        StockLevel.objects.bulk_create(
            StockLevel(barbershop_id=barbershop_id, product_id=pk, branch_id=main.pk, quantity=stock)
            for pk, stock in stocks
        )
        StockMovement.objects.filter(barbershop_id=barbershop_id, branch__isnull=True).update(branch_id=main.pk)


def backwards(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    StockLevel = apps.get_model("inventory", "StockLevel")
    for barbershop_id in each_barbershop(apps, schema_editor):
        total = (
            StockLevel.objects.filter(product_id=OuterRef("pk"))
            .values("product_id")
            .annotate(total=Sum("quantity"))
            .values("total")
        )
        Product.objects.filter(barbershop_id=barbershop_id).update(
            current_stock=Coalesce(Subquery(total), Value(0), output_field=IntegerField())
        )


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_stock_levels"),
        ("tenancy", "0006_membership_tenant_key"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
