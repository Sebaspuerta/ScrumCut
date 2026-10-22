"""Alcance de sede de cada petición (fase S2 de docs/sedes.md).

La barbería es la frontera de seguridad (RLS); la sede es una división operativa que
se aplica aquí. Selectores y servicios reciben un `BranchScope` y nunca leen `request`.
Un alcance solo vale para la membresía con la que se armó: así no se puede reusar el
de otra persona.
"""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet

from apps.tenancy.models import Branch, Membership
from apps.tenancy.roles import Role, role_has_permission

ONE = "una"
ALL = "todas"
WRITE_NEEDS_ONE_BRANCH = "Elige una sede para registrar esto: en «Todas las sedes» solo se consulta."
INACTIVE_BRANCH = "La sede no existe o está inactiva."


@dataclass(frozen=True)
class BranchScope:
    """Modo `una` (con su sede) o `todas`, y los ids de las sedes activas que la membresía puede usar."""

    membership_id: int
    mode: str
    branch: Branch | None
    allowed_ids: frozenset[int]

    @property
    def is_all(self) -> bool:
        return self.mode == ALL

    @property
    def token(self) -> str:
        """Lo que identifica al alcance en la sesión y en los formularios: el public_id de la sede o "todas"."""
        return ALL if self.is_all else str(self.branch.public_id) if self.branch else ""

    def check(self, membership: Membership) -> None:
        if membership is None or membership.pk != self.membership_id:
            raise PermissionDenied

    def apply(self, queryset: QuerySet, lookup: str = "branch") -> QuerySet:
        """El único filtro por sede. En "todas", toda la barbería, con el historial de las sedes inactivas."""
        if self.is_all:
            return queryset
        if self.branch is None:  # sin sedes permitidas: no ve nada
            return queryset.none()
        return queryset.filter(**{lookup: self.branch})

    def choices(self) -> QuerySet[Branch]:
        """Las sedes activas que esta membresía puede elegir, por nombre (el selector de sede)."""
        return Branch.objects.filter(pk__in=self.allowed_ids, is_active=True).order_by("name")

    def branches(self) -> QuerySet[Branch]:
        """Las sedes del alcance. En "todas", también las inactivas, como `apply` con su historial."""
        if self.is_all:
            return Branch.objects.all()
        if self.branch is None:
            return Branch.objects.none()
        return Branch.objects.filter(pk=self.branch.pk)

    def branch_for_write(self, membership: Membership) -> Branch:
        """Escribir exige una sede, y activa (decisión 14): en "todas" o sin sede, ValidationError.

        Se vuelve a leer de la base porque la sede pudo desactivarse después de armar el alcance.
        """
        self.check(membership)
        if self.is_all or self.branch is None:
            raise ValidationError({"branch": WRITE_NEEDS_ONE_BRANCH})
        try:
            return Branch.objects.get(pk=self.branch.pk, is_active=True)
        except Branch.DoesNotExist as exc:
            raise ValidationError({"branch": INACTIVE_BRANCH}) from exc

    def readable(self, membership: Membership, queryset: QuerySet, lookup: str = "branch") -> QuerySet:
        """Para leer un objeto por su código: el alcance de esta membresía y el filtro de `apply`.

        Un objeto de otra sede no se encuentra (`DoesNotExist`); en "todas", toda la barbería.
        """
        self.check(membership)
        return self.apply(queryset, lookup)

    def writable(self, membership: Membership, queryset: QuerySet, lookup: str = "branch") -> QuerySet:
        """El único filtro para escribir sobre un objeto que ya existe (fase S4a): solo los de la sede.

        Va antes del `select_for_update`. Un objeto de otra sede no se encuentra, igual que uno de
        otra barbería (`DoesNotExist`), para no revelar que existe. Exige una sede activa.
        """
        return queryset.filter(**{lookup: self.branch_for_write(membership)})


def allowed_branches(membership: Membership) -> QuerySet[Branch]:
    """Sedes activas por rol (decisión 1): con `sedes.ver`, todas; Cajero, las suyas; Barbero, las de su Barber."""
    active = Branch.objects.filter(is_active=True)
    if role_has_permission(membership.role, "sedes.ver"):
        return active
    if membership.role == Role.CASHIER:
        return active.filter(cashier_access__membership=membership)
    if membership.role == Role.BARBER:
        return active.filter(
            barber_links__barber__membership=membership, barber_links__barber__deleted_at__isnull=True
        ).distinct()
    return active.none()


def _one(membership: Membership, branches: list[Branch], chosen: Branch | None) -> BranchScope:
    return BranchScope(membership.pk, ONE, chosen, frozenset(branch.pk for branch in branches))


def _all(membership: Membership, branches: list[Branch]) -> BranchScope:
    return BranchScope(membership.pk, ALL, None, frozenset(branch.pk for branch in branches))


def resolve_scope(membership: Membership, requested: str | None = None) -> BranchScope:
    """El alcance pedido si es válido; si no, las reglas de docs/sedes.md en este orden:

    una sola sede permitida → esa; la última usada si sigue permitida; "todas" para quien
    tiene `sedes.ver`; la primera permitida por nombre. Sin sedes permitidas no ve nada.
    """
    branches = list(allowed_branches(membership).order_by("name"))
    can_see_all = role_has_permission(membership.role, "sedes.ver")
    by_token = {str(branch.public_id): branch for branch in branches}
    if requested == ALL and can_see_all:
        return _all(membership, branches)
    if requested in by_token:
        return _one(membership, branches, by_token[requested])
    if len(branches) == 1:
        return _one(membership, branches, branches[0])
    last = next((branch for branch in branches if branch.pk == membership.last_branch_id), None)
    if last is not None:
        return _one(membership, branches, last)
    if can_see_all:
        return _all(membership, branches)
    return _one(membership, branches, branches[0] if branches else None)
