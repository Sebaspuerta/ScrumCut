"""Barber.branch → BarberBranch (decisión 2 de docs/sedes.md).

Un barbero con sede queda en esa sede; uno con la sede nula, en todas las sedes activas
de su barbería.

Qué se pierde en la reversa: Barber.branch vuelve solo para el barbero con exactamente una sede;
el que tenía varias queda con la sede nula.
"""

from django.db import migrations

from apps.core.tenant_keys import each_barbershop


def forwards(apps, schema_editor):
    Barber = apps.get_model("staff", "Barber")
    BarberBranch = apps.get_model("staff", "BarberBranch")
    Branch = apps.get_model("tenancy", "Branch")
    for barbershop_id in each_barbershop(apps, schema_editor):
        active = list(Branch.objects.filter(barbershop_id=barbershop_id, is_active=True).values_list("pk", flat=True))
        links = [
            BarberBranch(barbershop_id=barbershop_id, barber_id=barber_id, branch_id=branch_id)
            for barber_id, own_branch in Barber.objects.filter(barbershop_id=barbershop_id).values_list("pk", "branch")
            for branch_id in ([own_branch] if own_branch else active)
        ]
        BarberBranch.objects.bulk_create(links)


def backwards(apps, schema_editor):
    Barber = apps.get_model("staff", "Barber")
    BarberBranch = apps.get_model("staff", "BarberBranch")
    for barbershop_id in each_barbershop(apps, schema_editor):
        branches_by_barber = {}
        for barber_id, branch_id in BarberBranch.objects.filter(barbershop_id=barbershop_id).values_list(
            "barber", "branch"
        ):
            branches_by_barber.setdefault(barber_id, []).append(branch_id)
        for barber_id, branch_ids in branches_by_barber.items():
            if len(branch_ids) == 1:
                Barber.objects.filter(pk=barber_id).update(branch_id=branch_ids[0])


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0002_barber_branches"),
        ("tenancy", "0005_main_branch_and_plan"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
