"""Paso 3 de 3 de Alert.branch: obligatoria, con llave compuesta, y una alerta abierta de producto por sede.

Qué se pierde en la reversa: la regla vuelve a ser una alerta abierta por (tipo, producto). Si hay
varias abiertas del mismo producto en distintas sedes, antes de restaurarla se resuelven todas
menos la más antigua.
"""

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone

from apps.core.tenant_keys import TenantKey, each_barbershop


def keep_one_open_alert_per_product(apps, schema_editor):
    Alert = apps.get_model("alerts", "Alert")
    for barbershop_id in each_barbershop(apps, schema_editor):
        seen = set()
        open_alerts = Alert.objects.filter(barbershop_id=barbershop_id, resolved_at__isnull=True, product__isnull=False)
        for pk, alert_type, product_id in open_alerts.order_by("pk").values_list("pk", "alert_type", "product_id"):
            if (alert_type, product_id) in seen:
                Alert.objects.filter(pk=pk).update(resolved_at=timezone.now())
            seen.add((alert_type, product_id))


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0003_alert_branch_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alert",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="alerts", to="tenancy.branch"
            ),
        ),
        TenantKey("alerts_alert"),
        migrations.RemoveConstraint(model_name="alert", name="uq_alert_open_per_product"),
        migrations.AddConstraint(
            model_name="alert",
            constraint=models.UniqueConstraint(
                condition=models.Q(("product__isnull", False), ("resolved_at__isnull", True)),
                fields=("alert_type", "product", "branch"),
                name="uq_alert_open_per_product_branch",
            ),
        ),
        # Va al final para que en la reversa corra antes de volver a la regla por (tipo, producto).
        migrations.RunPython(migrations.RunPython.noop, keep_one_open_alert_per_product),
    ]
