"""Escrituras de sedes (fase S1 de docs/sedes.md): alta, edición, activación y acceso del personal.

La sede se resuelve siempre con `Branch.objects`, que filtra por la barbería activa:
un identificador de otra barbería lanza `DoesNotExist` como en las demás apps; los
datos inválidos, `ValidationError`. Todas las escrituras se auditan.
"""

from collections.abc import Callable, Iterable
from typing import TypedDict
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Model, QuerySet

from apps.audit.models import record
from apps.cash.models import CashSession
from apps.staff.models import Barber, BarberBranch
from apps.tenancy.branch_scope import BranchScope, resolve_scope
from apps.tenancy.models import Barbershop, Branch, Membership, MembershipBranch
from apps.tenancy.permissions import ensure_member, ensure_permission
from apps.tenancy.roles import Role
from apps.tenancy.selectors import active_branches

PLAN_LIMIT = "El plan de la barbería permite hasta %(limit)s sedes activas."
DUPLICATE_NAME = "Ya existe una sede con ese nombre."
_TEXT_FIELDS = ("name", "address", "city", "phone")


class BranchData(TypedDict, total=False):
    name: str
    address: str
    city: str
    phone: str


def _audit(
    actor: Membership,
    action: str,
    *,
    obj: Model,
    before: dict | None,
    after: dict | None,
    branch: Branch | None = None,
) -> None:
    record(
        action=action,
        entity=obj._meta.label,
        entity_id=str(obj.public_id),
        actor=actor.user,
        barbershop=actor.barbershop,
        branch=branch,
        before=before,
        after=after,
    )


def _branch_snapshot(branch: Branch) -> dict:
    return {field: getattr(branch, field) for field in _TEXT_FIELDS} | {"is_active": branch.is_active}


def _branch_for_update(public_id: UUID | str) -> Branch:
    return Branch.objects.select_for_update().get(public_id=public_id)


def _check_plan_limit(membership: Membership) -> None:
    """Cuenta solo las sedes activas: desactivar una libera cupo (decisión 8).

    Bloquea la barbería para que dos altas simultáneas no pasen juntas el límite.
    """
    barbershop = Barbershop.objects.select_for_update().get(pk=membership.barbershop_id)
    if Branch.objects.filter(is_active=True).count() >= barbershop.max_branches:
        raise ValidationError(PLAN_LIMIT, code="plan_limit", params={"limit": barbershop.max_branches})


def _apply(branch: Branch, data: BranchData) -> None:
    unknown = set(data) - set(BranchData.__annotations__)
    if unknown:
        raise TypeError(f"Campos desconocidos: {sorted(unknown)}")
    for field in _TEXT_FIELDS:
        if field in data:
            setattr(branch, field, (data[field] or "").strip())


def _save_validated(branch: Branch) -> None:
    branch.full_clean()
    try:
        with transaction.atomic():
            branch.save()
    except IntegrityError as exc:
        # Dos solicitudes simultáneas pueden pasar full_clean con el mismo nombre: decide la base.
        raise ValidationError({"name": DUPLICATE_NAME}) from exc


# ── Sedes ────────────────────────────────────────────────────────────────────


def create_branch(membership: Membership, data: BranchData) -> Branch:
    ensure_permission(membership, "sedes.gestionar")
    with transaction.atomic():
        _check_plan_limit(membership)
        branch = Branch(barbershop_id=membership.barbershop_id)
        _apply(branch, data)
        _save_validated(branch)
        _audit(membership, "sede.crear", obj=branch, before=None, after=_branch_snapshot(branch), branch=branch)
    return branch


def update_branch(membership: Membership, branch: UUID | str, *, data: BranchData) -> Branch:
    """Solo cambia las claves presentes en `data`."""
    ensure_permission(membership, "sedes.gestionar")
    with transaction.atomic():
        target = _branch_for_update(branch)
        before = _branch_snapshot(target)
        _apply(target, data)
        _save_validated(target)
        after = _branch_snapshot(target)
        if after != before:
            _audit(membership, "sede.editar", obj=target, before=before, after=after, branch=target)
    return target


def deactivate_branch(membership: Membership, branch: UUID | str) -> Branch:
    """No con la caja abierta ni si es la única activa. La regla de citas futuras llega con la agenda."""
    ensure_permission(membership, "sedes.gestionar")
    with transaction.atomic():
        target = _branch_for_update(branch)
        if not target.is_active:
            return target
        if not Branch.objects.filter(is_active=True).exclude(pk=target.pk).exists():
            raise ValidationError("No se puede desactivar la única sede activa.", code="last_active_branch")
        if CashSession.objects.filter(branch=target, closed_at__isnull=True).exists():
            raise ValidationError("Cierra la caja de la sede antes de desactivarla.", code="open_cash_session")
        return _set_active(membership, target, active=False)


def activate_branch(membership: Membership, branch: UUID | str) -> Branch:
    ensure_permission(membership, "sedes.gestionar")
    with transaction.atomic():
        target = _branch_for_update(branch)
        if target.is_active:
            return target
        _check_plan_limit(membership)
        return _set_active(membership, target, active=True)


def _set_active(membership: Membership, branch: Branch, *, active: bool) -> Branch:
    before = _branch_snapshot(branch)
    branch.is_active = active
    branch.save(update_fields=["is_active", "updated_at"])
    action = "sede.reactivar" if active else "sede.desactivar"
    _audit(membership, action, obj=branch, before=before, after=_branch_snapshot(branch), branch=branch)
    return branch


# ── Acceso del personal (decisión 1) ─────────────────────────────────────────


def _replace_links(links: QuerySet, branches: list[Branch], *, build: Callable[[Branch], Model]) -> dict:
    """Deja exactamente `branches` en `links` y devuelve las sedes de antes y de después."""
    current = {link.branch_id: link.branch for link in links.select_related("branch")}
    wanted = {branch.pk: branch for branch in branches}
    links.filter(branch_id__in=set(current) - set(wanted)).delete()
    links.model.objects.bulk_create([build(branch) for pk, branch in wanted.items() if pk not in current])
    return {
        "before": {"branches": sorted(str(branch.public_id) for branch in current.values())},
        "after": {"branches": sorted(str(branch.public_id) for branch in branches)},
    }


def _cashier_for_update(membership: Membership, public_id: UUID | str) -> Membership:
    try:
        return Membership.objects.select_for_update().get(
            public_id=public_id, barbershop_id=membership.barbershop_id, role=Role.CASHIER
        )
    except Membership.DoesNotExist as exc:
        raise ValidationError({"cashier": "El cajero no existe en esta barbería."}) from exc


def set_cashier_branches(membership: Membership, cashier: UUID | str, *, branches: Iterable[UUID | str]) -> Membership:
    """Sedes a las que entra un Cajero. Membership no es TenantScopedModel: se filtra por la barbería."""
    ensure_permission(membership, "sedes.gestionar")
    chosen = active_branches(branches)
    with transaction.atomic():
        target = _cashier_for_update(membership, cashier)
        change = _replace_links(
            MembershipBranch.objects.filter(membership=target),
            chosen,
            build=lambda branch: MembershipBranch(
                barbershop_id=membership.barbershop_id, membership=target, branch=branch
            ),
        )
        _audit(membership, "sede.acceso_cajero", obj=target, before=change["before"], after=change["after"])
    return target


def set_barber_branches(membership: Membership, barber: UUID | str, *, branches: Iterable[UUID | str]) -> Barber:
    """Sedes donde trabaja un barbero; sin ninguna, no se puede elegir en comandas."""
    ensure_permission(membership, "sedes.gestionar")
    chosen = active_branches(branches)
    with transaction.atomic():
        target = Barber.objects.select_for_update().get(public_id=barber, deleted_at__isnull=True)
        change = _replace_links(
            BarberBranch.objects.filter(barber=target),
            chosen,
            build=lambda branch: BarberBranch(barbershop_id=target.barbershop_id, barber=target, branch=branch),
        )
        _audit(membership, "sede.barbero", obj=target, before=change["before"], after=change["after"])
    return target


# ── Cambio de sede (fase S2) ─────────────────────────────────────────────────


def choose_branch(membership: Membership, choice: str) -> BranchScope:
    """El alcance elegido: el public_id de una sede permitida o "todas" con `sedes.ver`; si no, PermissionDenied.

    Una sede elegida queda como la última usada, para volver a ella al iniciar sesión.
    """
    ensure_member(membership)
    scope = resolve_scope(membership, choice)
    if scope.token != choice:
        raise PermissionDenied
    if scope.branch is not None and membership.last_branch_id != scope.branch.pk:
        membership.last_branch = scope.branch
        membership.save(update_fields=["last_branch", "updated_at"])
    return scope
