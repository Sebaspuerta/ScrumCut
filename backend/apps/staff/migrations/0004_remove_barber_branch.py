"""Paso final de Barber.branch → BarberBranch: se borra el campo viejo.

La reversa vuelve a crear Barber.branch vacío (nullable); la reversa de 0003 lo llena solo para
los barberos con una sola sede. Los demás pierden su sede.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0003_barber_branches_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="barber",
            name="branch",
        ),
    ]
