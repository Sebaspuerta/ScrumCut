"""Paso 1 de 3 de Alert.branch (decisión 6 de docs/sedes.md): la columna, nullable.

Qué se pierde en la reversa: la sede de cada alerta.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
        ('tenancy', '0006_membership_tenant_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='branch',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='alerts', to='tenancy.branch'),
        ),
    ]
