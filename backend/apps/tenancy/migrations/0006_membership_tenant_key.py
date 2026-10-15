"""MembershipBranch.membership con llave compuesta: el acceso de un cajero no apunta a la membresía de otra
barbería. La reversa quita la llave y el único; no se pierden datos.
"""

from django.conf import settings
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0005_main_branch_and_plan'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='membership',
            constraint=models.UniqueConstraint(fields=('barbershop', 'id'), name='uq_membership_barbershop_id'),
        ),
        TenantKey("tenancy_membershipbranch", column="membership_id", references="tenancy_membership"),
    ]
