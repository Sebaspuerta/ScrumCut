"""Paso 1 de 3 del stock por sede (decisión 6 de docs/sedes.md): StockLevel con RLS y llaves compuestas,
StockMovement.branch todavía nullable, los tipos de traslado y `transfer_id`, que enlaza las dos
patas de un traslado.

Qué se pierde en la reversa: las existencias por sede (la reversa del paso 3 ya las sumó en
current_stock), la sede de cada movimiento y su `transfer_id`.
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

from apps.core.rls import EnableTenantRLS
from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_product_branch_prices'),
        ('tenancy', '0006_membership_tenant_key'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StockLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity', models.IntegerField(default=0, verbose_name='existencia')),
            ],
            options={
                'verbose_name': 'existencia en la sede',
            },
        ),
        migrations.RemoveConstraint(
            model_name='stockmovement',
            name='ck_stockmovement_type_valid',
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='branch',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='stock_movements', to='tenancy.branch'),
        ),
        migrations.AlterField(
            model_name='stockmovement',
            name='movement_type',
            field=models.CharField(choices=[('entrada', 'Entrada'), ('ajuste', 'Ajuste'), ('salida_venta', 'Salida por venta'), ('salida_servicio', 'Insumo de servicio'), ('reversion', 'Reversión'), ('traslado_salida', 'Traslado (salida)'), ('traslado_entrada', 'Traslado (entrada)')], max_length=16, verbose_name='tipo'),
        ),
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(condition=models.Q(('movement_type__in', ['entrada', 'ajuste', 'salida_venta', 'salida_servicio', 'reversion', 'traslado_salida', 'traslado_entrada'])), name='ck_stockmovement_type_valid'),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='transfer_id',
            field=models.UUIDField(blank=True, db_index=True, null=True, verbose_name='traslado'),
        ),
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(condition=models.Q(('transfer_id__isnull', True), ('movement_type__in', ['traslado_salida', 'traslado_entrada']), _connector='OR'), name='ck_stockmovement_transfer_id_only_on_transfers'),
        ),
        migrations.AddField(
            model_name='stocklevel',
            name='barbershop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.barbershop'),
        ),
        migrations.AddField(
            model_name='stocklevel',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stock_levels', to='tenancy.branch'),
        ),
        migrations.AddField(
            model_name='stocklevel',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stock_levels', to='inventory.product'),
        ),
        migrations.AddConstraint(
            model_name='stocklevel',
            constraint=models.UniqueConstraint(fields=('product', 'branch'), name='uq_stocklevel_product_branch'),
        ),
        migrations.AddConstraint(
            model_name='stocklevel',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gte', 0)), name='ck_stocklevel_not_negative'),
        ),
        EnableTenantRLS("inventory_stocklevel"),
        TenantKey("inventory_stocklevel"),
        TenantKey("inventory_stocklevel", column="product_id", references="inventory_product"),
    ]
