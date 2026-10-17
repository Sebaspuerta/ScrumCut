"""Servicios de sedes (fase S1 de docs/sedes.md): plan, desactivación, permisos, accesos y auditoría."""

from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.cash import services as cash
from apps.core.tenant_context import tenant_context
from apps.sales import services as sales
from apps.staff import services as staff
from apps.staff.models import BarberBranch
from apps.tenancy import services
from apps.tenancy.models import MAIN_BRANCH_NAME, Barbershop, Branch, MembershipBranch
from apps.tenancy.roles import Role
from tests.conftest import scope_of

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)


def _plan(shop, max_branches: int) -> None:
    Barbershop.objects.filter(pk=shop.pk).update(max_branches=max_branches)


def _main() -> Branch:
    return Branch.objects.get(name=MAIN_BRANCH_NAME)


# ── Límite del plan ──────────────────────────────────────────────────────────


def test_el_plan_por_defecto_admite_solo_la_sede_principal(owner):
    with pytest.raises(ValidationError) as error:
        services.create_branch(owner, {"name": "Norte"})
    assert error.value.code == "plan_limit"


def test_con_cupo_crea_la_sede_y_la_audita(owner, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": " Norte ", "city": "Bogotá"})

    assert (norte.name, norte.city, norte.is_active) == ("Norte", "Bogotá", True)
    assert AuditLog.objects.filter(action="sede.crear", entity_id=str(norte.public_id)).exists()


def test_el_cupo_cuenta_solo_las_sedes_activas(owner, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})
    services.deactivate_branch(owner, norte.public_id)

    sur = services.create_branch(owner, {"name": "Sur"})  # desactivar liberó el cupo

    with pytest.raises(ValidationError) as error:
        services.activate_branch(owner, norte.public_id)
    assert error.value.code == "plan_limit"
    assert sur.is_active and not Branch.objects.get(pk=norte.pk).is_active


def test_el_nombre_es_unico_en_la_barberia(owner, in_shop):
    _plan(in_shop, 2)
    with pytest.raises(ValidationError):
        services.create_branch(owner, {"name": MAIN_BRANCH_NAME})


# ── Desactivación ────────────────────────────────────────────────────────────


def test_no_se_desactiva_la_unica_sede_activa(owner, in_shop):
    with pytest.raises(ValidationError) as error:
        services.deactivate_branch(owner, _main().public_id)
    assert error.value.code == "last_active_branch"


def test_no_se_desactiva_una_sede_con_la_caja_abierta(owner, in_shop):
    _plan(in_shop, 2)
    services.create_branch(owner, {"name": "Norte"})
    main = _main()
    cash.open_session(owner, scope_of(owner, main), opening_amount=Decimal("0"))

    with pytest.raises(ValidationError) as error:
        services.deactivate_branch(owner, main.public_id)
    assert error.value.code == "open_cash_session"


def test_desactivar_y_reactivar_quedan_auditados(owner, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})

    services.deactivate_branch(owner, norte.public_id)
    services.activate_branch(owner, norte.public_id)

    actions = list(AuditLog.objects.filter(entity_id=str(norte.public_id)).values_list("action", flat=True))
    assert actions == ["sede.crear", "sede.desactivar", "sede.reactivar"]


def test_la_sede_de_otra_barberia_no_se_encuentra(owner, other_shop):
    with tenant_context(other_shop.pk):
        foreign = Branch.objects.get(name=MAIN_BRANCH_NAME)
    with pytest.raises(Branch.DoesNotExist):
        services.update_branch(owner, foreign.public_id, data={"name": "Intrusa"})


@pytest.mark.parametrize("role", [Role.CASHIER, Role.BARBER, Role.VIEWER])
def test_solo_dueno_y_administrador_gestionan_sedes(member, in_shop, role):
    with pytest.raises(PermissionDenied):
        services.update_branch(member(role, in_shop), _main().public_id, data={"name": "Otra"})


# ── Acceso del personal ──────────────────────────────────────────────────────


def test_el_cajero_queda_con_las_sedes_elegidas(owner, member, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})
    cashier = member(Role.CASHIER, in_shop)

    services.set_cashier_branches(owner, cashier.public_id, branches=[_main().public_id, norte.public_id])
    services.set_cashier_branches(owner, cashier.public_id, branches=[norte.public_id])

    assert list(MembershipBranch.objects.filter(membership=cashier).values_list("branch", flat=True)) == [norte.pk]
    assert AuditLog.objects.filter(action="sede.acceso_cajero").count() == 2


def test_el_acceso_por_sedes_es_solo_para_cajeros(owner, member, in_shop):
    with pytest.raises(ValidationError):
        services.set_cashier_branches(owner, member(Role.BARBER, in_shop).public_id, branches=[_main().public_id])


def test_no_se_asigna_una_sede_inactiva(owner, member, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})
    services.deactivate_branch(owner, norte.public_id)

    with pytest.raises(ValidationError):
        services.set_cashier_branches(owner, member(Role.CASHIER, in_shop).public_id, branches=[norte.public_id])


def _barber(owner, **kwargs):
    return staff.create_barber(
        owner, {"display_name": "Ana"}, commission_type="percentage", commission_value=40, **kwargs
    )


def _branches_of(barber) -> set[int]:
    return set(BarberBranch.objects.filter(barber=barber).values_list("branch", flat=True))


def test_con_una_sola_sede_activa_el_barbero_nuevo_queda_en_ella(owner, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})
    services.deactivate_branch(owner, norte.public_id)  # una sola activa, aunque haya dos

    assert _branches_of(_barber(owner)) == {_main().pk}


def test_con_varias_sedes_activas_el_barbero_nuevo_exige_sus_sedes(owner, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})

    with pytest.raises(ValidationError) as error:
        _barber(owner)
    assert "branches" in error.value.message_dict

    assert _branches_of(_barber(owner, branches=[norte.public_id])) == {norte.pk}


def test_el_barbero_nuevo_no_se_crea_en_una_sede_inactiva(owner, in_shop):
    _plan(in_shop, 2)
    norte = services.create_branch(owner, {"name": "Norte"})
    services.deactivate_branch(owner, norte.public_id)

    with pytest.raises(ValidationError):
        _barber(owner, branches=[norte.public_id])


def test_un_barbero_sin_sedes_no_se_puede_elegir_en_comandas(owner, in_shop):
    barber = _barber(owner)
    services.set_barber_branches(owner, barber.public_id, branches=[])

    with pytest.raises(ValidationError) as error:
        sales.create_order(owner, scope_of(owner, _main()), barber=barber.public_id)
    assert "barber" in error.value.message_dict
    assert AuditLog.objects.filter(action="sede.barbero", entity_id=str(barber.public_id)).exists()
