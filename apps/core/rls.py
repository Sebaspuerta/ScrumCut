"""Operación de migración que activa Row-Level Security en PostgreSQL.

Uso en la migración de cada tabla de negocio (desde la fase 1):

    operations = [
        ...,
        EnableTenantRLS("catalog_service"),
    ]

Requisito de despliegue: la aplicación se conecta con un rol de base de datos
que NO es superusuario ni dueño con BYPASSRLS; FORCE aplica la política incluso
al dueño de la tabla.
"""

from django.db.migrations.operations.base import Operation

_POLICY = "tenant_isolation"


class EnableTenantRLS(Operation):
    reversible = True
    reduces_to_sql = True

    def __init__(self, table: str) -> None:
        self.table = table

    def state_forwards(self, app_label, state) -> None:
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state) -> None:
        if schema_editor.connection.vendor != "postgresql":
            return
        quoted = schema_editor.quote_name(self.table)
        schema_editor.execute(f"ALTER TABLE {quoted} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {quoted} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(
            f"CREATE POLICY {_POLICY} ON {quoted} "
            "USING (barbershop_id = NULLIF(current_setting('app.current_barbershop', true), '')::bigint) "
            "WITH CHECK (barbershop_id = NULLIF(current_setting('app.current_barbershop', true), '')::bigint)"
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state) -> None:
        if schema_editor.connection.vendor != "postgresql":
            return
        quoted = schema_editor.quote_name(self.table)
        schema_editor.execute(f"DROP POLICY IF EXISTS {_POLICY} ON {quoted}")
        schema_editor.execute(f"ALTER TABLE {quoted} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {quoted} DISABLE ROW LEVEL SECURITY")

    def describe(self) -> str:
        return f"Activa Row-Level Security por barbería en {self.table}"
