"""Datos de S1 (docs/sedes.md): toda barbería con su Sede principal y su límite de sedes.

1. A la barbería sin sedes se le crea la "Sede principal" (paso 1 de la migración de datos).
2. max_branches = max(1, sedes activas actuales): ninguna barbería queda por encima de su plan.

Qué se pierde en la reversa: nada se borra. Las sedes creadas aquí se quedan, porque para entonces
otras tablas ya pueden usarlas; el límite del plan lo borra la reversa de 0004.
"""

from django.db import migrations

from apps.core.tenant_keys import each_barbershop

# Copiado de tenancy.models: una migración no depende de código que puede cambiar después.
MAIN_BRANCH_NAME = "Sede principal"


def forwards(apps, schema_editor):
    Barbershop = apps.get_model("tenancy", "Barbershop")
    Branch = apps.get_model("tenancy", "Branch")
    for barbershop_id in each_barbershop(apps, schema_editor):
        branches = Branch.objects.filter(barbershop_id=barbershop_id)
        if not branches.exists():
            Branch.objects.create(barbershop_id=barbershop_id, name=MAIN_BRANCH_NAME)
        active = branches.filter(is_active=True).count()
        Barbershop.objects.filter(pk=barbershop_id).update(max_branches=max(1, active))


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0004_branches_plan_hours_and_access"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
