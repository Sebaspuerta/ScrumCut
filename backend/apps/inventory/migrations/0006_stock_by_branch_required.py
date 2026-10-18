"""Paso 3 de 3 del stock por sede: StockMovement.branch obligatoria y sin Product.current_stock.

El total de la barbería pasa a ser la suma de las existencias por sede. Se agregan la llave
compuesta de la sede del movimiento y el índice (barbería, sede, fecha) de docs/sedes.md.

Qué se pierde en la reversa: nada más que lo del paso 2. `current_stock` vuelve con 0 y la
reversa del paso 2 lo llena con la suma de las sedes.
"""

import django.db.models.deletion
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_stock_levels_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockmovement",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="stock_movements", to="tenancy.branch"
            ),
        ),
        TenantKey("inventory_stockmovement"),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["barbershop", "branch", "created_at"], name="ix_stockmove_branch_created"),
        ),
        migrations.RemoveConstraint(model_name="product", name="ck_product_stock_not_negative"),
        migrations.RemoveField(model_name="product", name="current_stock"),
    ]
