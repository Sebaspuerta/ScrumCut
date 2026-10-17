"""Alcance de sede por rol y valores por defecto del middleware (fase S2 de docs/sedes.md)."""

import pytest
from django.core.exceptions import PermissionDenied

from apps.staff import services as staff
from apps.tenancy import services as tenancy
from apps.tenancy.branch_scope import ALL, BranchScope, resolve_scope
from apps.tenancy.models import Barbershop, Branch, Membership, MembershipBranch
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db


@pytest.fixture
def centro_y_norte(member, in_shop):
    """Centro (la Sede principal renombrada) y Norte, con el plan para tres sedes."""
    Barbershop.objects.filter(pk=in_shop.pk).update(max_branches=3)
    owner = member(Role.OWNER, in_shop)
    centro = Branch.objects.get()
    tenancy.update_branch(owner, centro.public_id, data={"name": "Centro"})
    norte = tenancy.create_branch(owner, {"name": "Norte"})
    return owner, Branch.objects.get(pk=centro.pk), norte


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN, Role.VIEWER])
def test_quien_ve_todas_entra_al_consolidado_con_varias_sedes(member, in_shop, centro_y_norte, role):
    owner, centro, norte = centro_y_norte
    scope = resolve_scope(owner if role == Role.OWNER else member(role, in_shop))

    assert scope.is_all and scope.allowed_ids == {centro.pk, norte.pk}


def test_con_una_sola_sede_el_dueno_entra_a_ella(member, in_shop):
    scope = resolve_scope(member(Role.OWNER, in_shop))
    assert (scope.mode, scope.branch) == ("una", Branch.objects.get())


def test_la_ultima_sede_usada_manda_si_sigue_permitida(centro_y_norte):
    owner, _, norte = centro_y_norte
    tenancy.choose_branch(owner, str(norte.public_id))
    owner.refresh_from_db()

    assert resolve_scope(owner).branch == norte


def test_el_cajero_entra_solo_a_sus_sedes_y_por_defecto_a_la_primera(member, in_shop, centro_y_norte):
    owner, centro, norte = centro_y_norte
    cashier = member(Role.CASHIER, in_shop)
    tenancy.set_cashier_branches(owner, cashier.public_id, branches=[norte.public_id, centro.public_id])

    scope = resolve_scope(cashier)
    assert (scope.branch, scope.allowed_ids) == (centro, {centro.pk, norte.pk})  # la primera por nombre
    assert resolve_scope(cashier, ALL).branch == centro  # sin sedes.ver no hay "todas"


def test_el_cajero_sin_sedes_no_ve_nada(member, in_shop, centro_y_norte):
    scope = resolve_scope(member(Role.CASHIER, in_shop))
    assert scope.branch is None and not scope.allowed_ids
    assert not scope.apply(Branch.objects.all()).exists()


def test_el_barbero_entra_a_las_sedes_de_su_barbero(member, in_shop, centro_y_norte):
    owner, centro, norte = centro_y_norte
    login = member(Role.BARBER, in_shop)
    staff.create_barber(
        owner,
        {"display_name": "Ana", "membership": login.public_id},
        commission_type="percentage",
        commission_value=40,
        branches=[norte.public_id],
    )

    scope = resolve_scope(login)
    assert (scope.branch, scope.allowed_ids) == (norte, {norte.pk})


def test_una_sede_inactiva_queda_fuera_del_alcance(member, in_shop, centro_y_norte):
    owner, centro, norte = centro_y_norte
    cashier = member(Role.CASHIER, in_shop)
    tenancy.set_cashier_branches(owner, cashier.public_id, branches=[centro.public_id, norte.public_id])
    tenancy.deactivate_branch(owner, norte.public_id)

    assert resolve_scope(cashier, str(norte.public_id)).branch == centro
    assert resolve_scope(owner).allowed_ids == {centro.pk}
    assert MembershipBranch.objects.filter(branch=norte).exists()  # el acceso queda; la sede no entra


def test_un_alcance_no_sirve_para_otra_membresia(member, in_shop, centro_y_norte):
    owner = centro_y_norte[0]
    other = Membership.objects.get(pk=member(Role.ADMIN, in_shop).pk)
    with pytest.raises(PermissionDenied):
        resolve_scope(owner).check(other)


def test_el_alcance_es_inmutable(centro_y_norte):
    scope: BranchScope = resolve_scope(centro_y_norte[0])
    with pytest.raises(AttributeError):  # dataclasses.FrozenInstanceError
        scope.mode = "una"
