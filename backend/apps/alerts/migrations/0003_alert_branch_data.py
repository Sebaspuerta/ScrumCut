"""Paso 2 de 3 de Alert.branch: las alertas que ya existían quedan con una sede.

Las de producto, con la Sede principal de su barbería (la más antigua: ahí quedó todo el stock
en la migración de inventario); las de fiado, con la sede de origen del fiado.

La reversa no hace nada aquí; la del paso 1 borra la columna y con ella la sede de cada alerta.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery

from apps.core.tenant_keys import each_barbershop


def forwards(apps, schema_editor):
    Alert = apps.get_model("alerts", "Alert")
    Branch = apps.get_model("tenancy", "Branch")
    Receivable = apps.get_model("receivables", "Receivable")
    for barbershop_id in each_barbershop(apps, schema_editor):
        alerts = Alert.objects.filter(barbershop_id=barbershop_id, branch__isnull=True)
        origin = Receivable.objects.filter(pk=OuterRef("receivable_id")).values("origin_branch_id")[:1]
        alerts.filter(receivable__isnull=False).update(branch_id=Subquery(origin))
        main = Branch.objects.filter(barbershop_id=barbershop_id).order_by("pk").values_list("pk", flat=True).first()
        alerts.filter(product__isnull=False).update(branch_id=main)


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0002_alert_branch"),
        ("receivables", "0004_origin_branch_required"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
