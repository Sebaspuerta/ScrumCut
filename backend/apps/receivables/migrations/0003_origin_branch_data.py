"""Paso 2 de 3 de Receivable.origin_branch (decisión 3 de docs/sedes.md).

El fiado de una comanda toma la sede de la comanda; el manual, la Sede principal de su
barbería (la más antigua). El paso 1 agregó la columna nullable y el 3 la vuelve obligatoria.

La reversa no hace nada aquí; la del paso 1 borra la columna y con ella la sede de origen.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery

from apps.core.tenant_keys import each_barbershop


def forwards(apps, schema_editor):
    Receivable = apps.get_model("receivables", "Receivable")
    Order = apps.get_model("sales", "Order")
    Branch = apps.get_model("tenancy", "Branch")
    for barbershop_id in each_barbershop(apps, schema_editor):
        receivables = Receivable.objects.filter(barbershop_id=barbershop_id)
        order_branch = Order.objects.filter(pk=OuterRef("order_id")).values("branch_id")[:1]
        receivables.filter(order__isnull=False).update(origin_branch_id=Subquery(order_branch))
        main_branch = Branch.objects.filter(barbershop_id=barbershop_id).order_by("pk").values_list("pk", flat=True)
        receivables.filter(origin_branch__isnull=True).update(origin_branch_id=main_branch.first())


class Migration(migrations.Migration):

    dependencies = [
        ("receivables", "0002_origin_branch"),
        ("sales", "0002_order_branch_index"),
        ("tenancy", "0005_main_branch_and_plan"),
    ]

    operations = [
        # La reversa no hace nada: deshacer el paso 1 borra la columna.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
