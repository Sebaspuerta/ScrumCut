from django.db import migrations

# Como EnableTenantRLS, más una excepción: sin barbería activa (tareas de plataforma)
# se ven y se escriben los eventos de plataforma, que no tienen barbería.
_ACTIVE = "NULLIF(current_setting('app.current_barbershop', true), '')::bigint"
_RULE = f"(barbershop_id = {_ACTIVE} OR (barbershop_id IS NULL AND {_ACTIVE} IS NULL))"


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE audit_auditlog ENABLE ROW LEVEL SECURITY",
                "ALTER TABLE audit_auditlog FORCE ROW LEVEL SECURITY",
                f"CREATE POLICY tenant_isolation ON audit_auditlog USING {_RULE} WITH CHECK {_RULE}",
            ],
            reverse_sql=[
                "DROP POLICY IF EXISTS tenant_isolation ON audit_auditlog",
                "ALTER TABLE audit_auditlog NO FORCE ROW LEVEL SECURITY",
                "ALTER TABLE audit_auditlog DISABLE ROW LEVEL SECURITY",
            ],
        ),
    ]
