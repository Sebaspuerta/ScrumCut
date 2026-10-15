"""Índice (barbershop, branch, opened_at) y llave compuesta hacia la sede en las cajas.

La reversa quita el índice y la llave; no se pierden datos.
"""

from django.conf import settings
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('cash', '0002_refund_kind'),
        ('tenancy', '0004_branches_plan_hours_and_access'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='cashsession',
            index=models.Index(fields=['barbershop', 'branch', 'opened_at'], name='ix_cashsession_branch_opened'),
        ),
        TenantKey("cash_cashsession"),
    ]
