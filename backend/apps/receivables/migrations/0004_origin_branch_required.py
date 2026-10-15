"""Paso 3 de 3 de Receivable.origin_branch: obligatoria y con la llave compuesta hacia la sede.

La reversa la vuelve nullable y quita la llave; no se pierden datos.
"""

import django.db.models.deletion
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ("receivables", "0003_origin_branch_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="receivable",
            name="origin_branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="tenancy.branch",
                verbose_name="sede de origen",
            ),
        ),
        TenantKey("receivables_receivable", column="origin_branch_id"),
    ]
