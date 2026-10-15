"""BarberBranch.barber con llave compuesta: la sede de un barbero no apunta al barbero de otra barbería.
La reversa quita la llave y el único; no se pierden datos.
"""

from django.conf import settings
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0004_remove_barber_branch'),
        ('tenancy', '0006_membership_tenant_key'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='barber',
            constraint=models.UniqueConstraint(fields=('barbershop', 'id'), name='uq_barber_barbershop_id'),
        ),
        TenantKey("staff_barberbranch", column="barber_id", references="staff_barber"),
    ]
