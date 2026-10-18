"""Precio de servicio por sede (decisión 17 de docs/sedes.md), con RLS y llaves compuestas hacia la
sede y hacia el servicio.

Qué se pierde en la reversa: los precios fijados por sede; las comandas ya guardaron el suyo en el ítem.
"""

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models

from apps.core.rls import EnableTenantRLS
from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
        ('tenancy', '0006_membership_tenant_key'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceBranchPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='precio en la sede')),
            ],
            options={
                'verbose_name': 'precio de servicio en la sede',
            },
        ),
        migrations.AddConstraint(
            model_name='service',
            constraint=models.UniqueConstraint(fields=('barbershop', 'id'), name='uq_service_barbershop_id'),
        ),
        migrations.AddField(
            model_name='servicebranchprice',
            name='barbershop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.barbershop'),
        ),
        migrations.AddField(
            model_name='servicebranchprice',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='service_prices', to='tenancy.branch'),
        ),
        migrations.AddField(
            model_name='servicebranchprice',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='branch_prices', to='catalog.service'),
        ),
        migrations.AddConstraint(
            model_name='servicebranchprice',
            constraint=models.UniqueConstraint(fields=('service', 'branch'), name='uq_servicebranchprice_service_branch'),
        ),
        migrations.AddConstraint(
            model_name='servicebranchprice',
            constraint=models.CheckConstraint(condition=models.Q(('price__gte', 0)), name='ck_servicebranchprice_not_negative'),
        ),
        EnableTenantRLS("catalog_servicebranchprice"),
        TenantKey("catalog_servicebranchprice"),
        TenantKey("catalog_servicebranchprice", column="service_id", references="catalog_service"),
    ]
