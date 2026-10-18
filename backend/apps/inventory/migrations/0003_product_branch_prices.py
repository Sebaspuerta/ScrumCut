"""Precio de producto por sede (decisión 17 de docs/sedes.md), con RLS y llaves compuestas hacia la
sede y hacia el producto.

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
        ('inventory', '0002_stockmovement_reference'),
        ('tenancy', '0006_membership_tenant_key'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductBranchPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='precio en la sede')),
            ],
            options={
                'verbose_name': 'precio de producto en la sede',
            },
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(fields=('barbershop', 'id'), name='uq_product_barbershop_id'),
        ),
        migrations.AddField(
            model_name='productbranchprice',
            name='barbershop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.barbershop'),
        ),
        migrations.AddField(
            model_name='productbranchprice',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='product_prices', to='tenancy.branch'),
        ),
        migrations.AddField(
            model_name='productbranchprice',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='branch_prices', to='inventory.product'),
        ),
        migrations.AddConstraint(
            model_name='productbranchprice',
            constraint=models.UniqueConstraint(fields=('product', 'branch'), name='uq_productbranchprice_product_branch'),
        ),
        migrations.AddConstraint(
            model_name='productbranchprice',
            constraint=models.CheckConstraint(condition=models.Q(('price__gte', 0)), name='ck_productbranchprice_not_negative'),
        ),
        EnableTenantRLS("inventory_productbranchprice"),
        TenantKey("inventory_productbranchprice"),
        TenantKey("inventory_productbranchprice", column="product_id", references="inventory_product"),
    ]
