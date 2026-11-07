"""Llave del intento en los movimientos de stock que registra la app (entrada, ajuste y salida de un traslado),
única por barbería cuando existe, como la del cobro rápido.

Los movimientos existentes quedan con la llave nula. La reversa quita la restricción y la columna; no se pierden
otros datos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0006_stock_by_branch_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovement",
            name="request_key",
            field=models.UUIDField(blank=True, editable=False, null=True, verbose_name="llave del intento"),
        ),
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.UniqueConstraint(
                condition=models.Q(("request_key__isnull", False)),
                fields=("barbershop", "request_key"),
                name="uq_stockmovement_request_key_per_barbershop",
            ),
        ),
    ]
