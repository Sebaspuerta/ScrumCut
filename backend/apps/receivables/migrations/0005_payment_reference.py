"""La referencia de un abono (Nequi 4821), opcional y del mismo largo que la del pago de una comanda.

Solo agrega la columna: los abonos que ya existen quedan sin referencia (vacía) y no se modifican. La reversa
quita la columna.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("receivables", "0004_origin_branch_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="receivablepayment",
            name="reference",
            field=models.CharField(blank=True, max_length=80, verbose_name="referencia"),
        ),
    ]
