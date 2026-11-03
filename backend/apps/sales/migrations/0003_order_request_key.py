"""Llave del intento de cobro rápido en la comanda, única por barbería cuando existe.

Las comandas existentes quedan con la llave nula. La reversa quita la restricción y la columna; no se pierden
otros datos.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_order_branch_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='request_key',
            field=models.UUIDField(blank=True, editable=False, null=True, verbose_name='llave del cobro'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(
                condition=models.Q(('request_key__isnull', False)),
                fields=('barbershop', 'request_key'),
                name='uq_order_request_key_per_barbershop',
            ),
        ),
    ]
