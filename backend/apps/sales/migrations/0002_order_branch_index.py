"""Índice (barbershop, branch, closed_at) y llave compuesta hacia la sede en las comandas.

La reversa quita el índice y la llave; no se pierden datos.
"""

from django.conf import settings
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('sales', '0001_initial'),
        ('staff', '0002_barber_branches'),
        ('tenancy', '0004_branches_plan_hours_and_access'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['barbershop', 'branch', 'closed_at'], name='ix_order_branch_closed'),
        ),
        TenantKey("sales_order"),
    ]
