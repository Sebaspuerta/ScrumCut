"""Precios por sede de servicios y productos (decisión 17 de docs/sedes.md, fase S4a).

El catálogo es común a la barbería; cada sede puede fijar su propio precio. Sin precio de la
sede, rige el del catálogo. `current_price` es la única forma de resolverlo: la usan las
comandas al agregar un ítem, que guardan ese precio en el ítem (regla 10).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, F, OuterRef, QuerySet, Subquery
from django.db.models.functions import Coalesce

from apps.audit.models import record
from apps.catalog.models import Service, ServiceBranchPrice
from apps.inventory.models import Product, ProductBranchPrice
from apps.tenancy.branch_scope import BranchScope
from apps.tenancy.models import Branch, Membership
from apps.tenancy.permissions import ensure_permission

_CENTS = Decimal("0.01")

# Por tipo de ítem: modelo del precio por sede, campo que apunta al ítem, permiso para cambiarlo
# (solo Dueño y Administrador lo tienen) y campo del precio del catálogo.
_PRICES = {
    Service: (ServiceBranchPrice, "service", "servicios.editar", "price"),
    Product: (ProductBranchPrice, "product", "inventario.editar", "sale_price"),
}


def with_current_price(items: QuerySet, branch: Branch) -> QuerySet:
    """Anota `price_now` en cada servicio o producto: el de la sede o, si no fijó uno, el del catálogo.

    Una sola consulta para toda la lista (la pantalla de comandas muestra el catálogo con su precio).
    """
    model, field, _, catalog_field = _PRICES[items.model]
    own = model.objects.filter(branch=branch, **{field: OuterRef("pk")}).values("price")[:1]
    return items.annotate(price_now=Coalesce(Subquery(own), F(catalog_field), output_field=DecimalField()))


def current_price(item: Service | Product, branch: Branch) -> Decimal:
    """El precio vigente del ítem en la sede. La única regla: la misma anotación de `with_current_price`."""
    return with_current_price(type(item).objects.filter(pk=item.pk), branch).values_list("price_now", flat=True).get()


def _snapshot(price) -> dict:
    return {"branch": str(price.branch.public_id), "price": str(Decimal(price.price).quantize(_CENTS))}


def _audit(membership: Membership, action: str, *, price, before: dict | None, after: dict | None) -> None:
    record(
        action=action,
        entity=price._meta.label,
        entity_id=str(price.public_id),
        actor=membership.user,
        barbershop=membership.barbershop,
        branch=price.branch,
        before=before,
        after=after,
    )


def set_branch_price(membership: Membership, item: Service | Product, *, scope: BranchScope, price: Decimal):
    """Fija o cambia el precio del ítem en la sede del alcance. Las comandas ya cerradas no cambian."""
    model, field, permission, _ = _PRICES[type(item)]
    ensure_permission(membership, permission)
    branch = scope.branch_for_write(membership)
    with transaction.atomic():
        existing = model.objects.select_for_update().filter(branch=branch, **{field: item}).first()
        before = _snapshot(existing) if existing else None
        target = existing or model(barbershop_id=membership.barbershop_id, branch=branch, **{field: item})
        target.price = Decimal(price)
        target.full_clean()
        target.save()
        _audit(membership, "precio_sede.fijar", price=target, before=before, after=_snapshot(target))
    return target


def remove_branch_price(membership: Membership, item: Service | Product, *, scope: BranchScope) -> None:
    """Quita el precio de la sede del alcance: vuelve a regir el del catálogo."""
    model, field, permission, _ = _PRICES[type(item)]
    ensure_permission(membership, permission)
    branch = scope.branch_for_write(membership)
    with transaction.atomic():
        existing = model.objects.select_for_update().filter(branch=branch, **{field: item}).first()
        if existing is None:
            raise ValidationError({"price": "La sede no tiene un precio propio para este ítem."})
        _audit(membership, "precio_sede.quitar", price=existing, before=_snapshot(existing), after=None)
        existing.delete()
