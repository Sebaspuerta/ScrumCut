"""AuditLog.branch (opcional) con llave compuesta hacia la sede.

La reversa borra la columna: los eventos conservan todo menos la sede en la que ocurrieron.
"""

import django.db.models.deletion
from django.db import migrations, models

from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_auditlog_rls'),
        ('tenancy', '0006_membership_tenant_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tenancy.branch'),
        ),
        TenantKey("audit_auditlog"),
    ]
