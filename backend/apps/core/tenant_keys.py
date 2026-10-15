"""Integridad entre barberías en la base de datos (docs/sedes.md, "Llave compuesta").

PostgreSQL no aplica RLS a las llaves foráneas: con una FK simple, una fila de la
barbería A podría apuntar a la sede (o a la membresía, o al barbero) de la barbería B.
La llave compuesta (barbershop_id, <columna>) → <tabla> (barbershop_id, id) lo impide
en la base. La tabla destino necesita su único (barbershop, id).
"""

from collections.abc import Iterator

from django.db.migrations.operations.base import Operation


class TenantKey(Operation):
    """FOREIGN KEY (barbershop_id, <column>) REFERENCES <references> (barbershop_id, id). Reversible.

    Por defecto apunta a la sede. Diferible como las FK de Django. Con la columna nula
    la llave no se revisa (MATCH SIMPLE).
    """

    reversible = True
    reduces_to_sql = True

    def __init__(self, table: str, column: str = "branch_id", references: str = "tenancy_branch") -> None:
        self.table = table
        self.column = column
        self.references = references

    @property
    def constraint(self) -> str:
        return f"fk_{self.table}_{self.column}_tenant"

    def state_forwards(self, app_label, state) -> None:
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state) -> None:
        if schema_editor.connection.vendor != "postgresql":
            return
        quote = schema_editor.quote_name
        schema_editor.execute(
            f"ALTER TABLE {quote(self.table)} ADD CONSTRAINT {quote(self.constraint)} "
            f"FOREIGN KEY (barbershop_id, {quote(self.column)}) "
            f"REFERENCES {quote(self.references)} (barbershop_id, id) DEFERRABLE INITIALLY DEFERRED"
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state) -> None:
        if schema_editor.connection.vendor != "postgresql":
            return
        quote = schema_editor.quote_name
        schema_editor.execute(f"ALTER TABLE {quote(self.table)} DROP CONSTRAINT {quote(self.constraint)}")

    def describe(self) -> str:
        return f"Llave compuesta (barbershop_id, {self.column}) hacia {self.references} en {self.table}"


def each_barbershop(apps, schema_editor) -> Iterator[int]:
    """Para migraciones de datos: fija cada barbería antes de leer o escribir sus filas.

    Con FORCE RLS ni el dueño de las tablas ve filas sin barbería fijada; el valor es
    local a la transacción de la migración y se limpia al terminar.
    """
    barbershop_ids = list(apps.get_model("tenancy", "Barbershop").objects.values_list("pk", flat=True))
    postgres = schema_editor.connection.vendor == "postgresql"
    with schema_editor.connection.cursor() as cursor:
        for barbershop_id in barbershop_ids:
            if postgres:
                cursor.execute("SELECT set_config('app.current_barbershop', %s, true)", [str(barbershop_id)])
            yield barbershop_id
        if postgres:
            cursor.execute("SELECT set_config('app.current_barbershop', '', true)")
