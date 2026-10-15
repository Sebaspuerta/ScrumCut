"""Paso 1 de 3 de Receivable.origin_branch: la columna, nullable (decisión 3 de docs/sedes.md).

Qué se pierde en la reversa: la sede de origen de cada fiado.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receivables', '0001_initial'),
        ('tenancy', '0004_branches_plan_hours_and_access'),
    ]

    operations = [
        migrations.AddField(
            model_name='receivable',
            name='origin_branch',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tenancy.branch', verbose_name='sede de origen'),
        ),
    ]
