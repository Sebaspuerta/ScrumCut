"""BarberBranch con RLS y llave compuesta hacia la sede (decisión 2 de docs/sedes.md).

Qué se pierde en la reversa: las sedes de cada barbero. Antes, la reversa de 0003 devuelve
Barber.branch solo a los barberos con una sola sede.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models

from apps.core.rls import EnableTenantRLS
from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0001_initial'),
        ('tenancy', '0004_branches_plan_hours_and_access'),
    ]

    operations = [
        migrations.CreateModel(
            name='BarberBranch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('barber', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='branch_links', to='staff.barber')),
                ('barbershop', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.barbershop')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='barber_links', to='tenancy.branch')),
            ],
            options={
                'verbose_name': 'sede del barbero',
                'constraints': [models.UniqueConstraint(fields=('barber', 'branch'), name='uq_barberbranch_barber_branch')],
            },
        ),
        EnableTenantRLS("staff_barberbranch"),
        TenantKey("staff_barberbranch"),
    ]
