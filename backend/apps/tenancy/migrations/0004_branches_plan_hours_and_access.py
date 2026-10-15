"""Fase S1 de docs/sedes.md: ciudad y único (barbershop, id) en la sede, límite del plan, última sede,
horarios (BranchHours) y acceso de cajeros (MembershipBranch), con RLS y llaves compuestas.

Qué se pierde en la reversa: los horarios, los accesos de cajeros, la última sede de cada membresía,
la ciudad de cada sede y el límite del plan.
"""

import django.core.validators
import django.db.models.deletion
import uuid
from django.db import migrations, models

from apps.core.rls import EnableTenantRLS
from apps.core.tenant_keys import TenantKey


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0003_order_number_and_credit_limit'),
    ]

    operations = [
        migrations.CreateModel(
            name='BranchHours',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('weekday', models.PositiveSmallIntegerField(choices=[(0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')], validators=[django.core.validators.MaxValueValidator(6)], verbose_name='día')),
                ('opens_at', models.TimeField(blank=True, null=True, verbose_name='abre')),
                ('closes_at', models.TimeField(blank=True, null=True, verbose_name='cierra')),
                ('is_closed', models.BooleanField(default=False, verbose_name='cerrado')),
            ],
            options={
                'verbose_name': 'horario de sede',
            },
        ),
        migrations.CreateModel(
            name='MembershipBranch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'acceso de cajero a sede',
            },
        ),
        migrations.AddField(
            model_name='barbershop',
            name='max_branches',
            field=models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='sedes del plan'),
        ),
        migrations.AddField(
            model_name='branch',
            name='city',
            field=models.CharField(blank=True, max_length=80, verbose_name='ciudad'),
        ),
        migrations.AddField(
            model_name='membership',
            name='last_branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tenancy.branch', verbose_name='última sede'),
        ),
        migrations.AddConstraint(
            model_name='branch',
            constraint=models.UniqueConstraint(fields=('barbershop', 'id'), name='uq_branch_barbershop_id'),
        ),
        migrations.AddField(
            model_name='branchhours',
            name='barbershop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.barbershop'),
        ),
        migrations.AddField(
            model_name='branchhours',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='hours', to='tenancy.branch'),
        ),
        migrations.AddField(
            model_name='membershipbranch',
            name='barbershop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.barbershop'),
        ),
        migrations.AddField(
            model_name='membershipbranch',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cashier_access', to='tenancy.branch'),
        ),
        migrations.AddField(
            model_name='membershipbranch',
            name='membership',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='branch_access', to='tenancy.membership'),
        ),
        migrations.AddConstraint(
            model_name='branchhours',
            constraint=models.UniqueConstraint(fields=('branch', 'weekday'), name='uq_branchhours_branch_weekday'),
        ),
        migrations.AddConstraint(
            model_name='branchhours',
            constraint=models.CheckConstraint(condition=models.Q(('weekday__lte', 6)), name='ck_branchhours_weekday'),
        ),
        migrations.AddConstraint(
            model_name='branchhours',
            constraint=models.CheckConstraint(condition=models.Q(('is_closed', True), models.Q(('closes_at__isnull', False), ('opens_at__isnull', False), ('opens_at__lt', models.F('closes_at'))), _connector='OR'), name='ck_branchhours_opens_before_closes'),
        ),
        migrations.AddConstraint(
            model_name='membershipbranch',
            constraint=models.UniqueConstraint(fields=('membership', 'branch'), name='uq_membershipbranch_membership_branch'),
        ),
        EnableTenantRLS("tenancy_branchhours"),
        EnableTenantRLS("tenancy_membershipbranch"),
        TenantKey("tenancy_branchhours"),
        TenantKey("tenancy_membershipbranch"),
        TenantKey("tenancy_membership", column="last_branch_id"),
    ]
