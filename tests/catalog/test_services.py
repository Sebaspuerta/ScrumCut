from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.catalog import selectors, services
from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db


def _create(membership, name="Corte fade", **extra) -> Service:
    data = {"price": Decimal("25000"), "duration_minutes": 30, **extra}
    return services.create_service(membership, name=name, **data)


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)


@pytest.fixture
def admin(member, in_shop):
    return member(Role.ADMIN, in_shop)


# ── Regla 38: nombre único por barbería ──────────────────────────────────────


def test_crear_servicio_guarda_los_datos_y_audita(owner):
    service = _create(owner, name="  Corte fade  ", description="Con máquina")

    assert service.name == "Corte fade"
    assert service.price == Decimal("25000")
    log = AuditLog.objects.get(action="servicio.crear")
    assert log.entity_id == str(service.public_id)
    assert log.actor == owner.user
    assert log.before is None
    assert log.after["price"] == "25000.00"


def test_el_nombre_no_distingue_mayusculas(owner):
    _create(owner, name="Corte fade")
    with pytest.raises(ValidationError):
        _create(owner, name="CORTE FADE")
    assert Service.objects.count() == 1


def test_renombrar_a_un_nombre_existente_falla(owner):
    _create(owner, name="Corte fade")
    barba = _create(owner, name="Barba")
    with pytest.raises(ValidationError):
        services.update_service(owner, barba.public_id, name="corte fade")


def test_un_servicio_desactivado_sigue_reservando_su_nombre(owner):
    service = _create(owner)
    services.deactivate_service(owner, service.public_id)
    with pytest.raises(ValidationError):
        _create(owner, name="corte fade")


def test_un_servicio_borrado_libera_su_nombre(owner):
    service = _create(owner)
    services.soft_delete_service(owner, service.public_id)
    assert _create(owner, name="Corte fade").pk != service.pk


def test_dos_barberias_pueden_usar_el_mismo_nombre(member, shop, other_shop):
    with tenant_context(shop.pk):
        _create(member(Role.OWNER, shop))
    with tenant_context(other_shop.pk):
        _create(member(Role.OWNER, other_shop))
        assert selectors.list_services().count() == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [("price", Decimal("-1")), ("duration_minutes", 0), ("name", "   ")],
)
def test_datos_invalidos_se_rechazan(owner, field, value):
    data = {"name": "Corte fade", "price": Decimal("25000"), "duration_minutes": 30, field: value}
    with pytest.raises(ValidationError):
        services.create_service(owner, **data)


# ── Regla 39: desactivar y borrado lógico ────────────────────────────────────


def test_desactivar_lo_saca_de_la_lista_activa_pero_no_del_catalogo(owner):
    service = _create(owner)
    services.deactivate_service(owner, service.public_id)

    assert list(selectors.list_services()) == []
    assert list(selectors.list_services(active_only=False)) == [service]
    assert selectors.get_service(service.public_id).is_active is False

    services.activate_service(owner, service.public_id)
    assert list(selectors.list_services()) == [service]
    assert list(AuditLog.objects.values_list("action", flat=True).order_by("pk")) == [
        "servicio.crear",
        "servicio.desactivar",
        "servicio.activar",
    ]


def test_un_servicio_borrado_desaparece_y_no_se_edita(owner):
    service = _create(owner)
    services.soft_delete_service(owner, service.public_id)

    assert list(selectors.list_services(active_only=False)) == []
    with pytest.raises(Service.DoesNotExist):
        selectors.get_service(service.public_id)
    with pytest.raises(Service.DoesNotExist):
        services.update_service(owner, service.public_id, price=Decimal("1"))

    service.refresh_from_db()
    assert service.deleted_by == owner.user
    log = AuditLog.objects.get(action="servicio.eliminar")
    assert log.before["deleted_at"] is None
    assert log.after["deleted_at"] is not None


def test_editar_solo_cambia_lo_recibido_y_audita_antes_y_despues(owner):
    service = _create(owner, description="Original")
    services.update_service(owner, service.public_id, price=Decimal("30000"))

    service.refresh_from_db()
    assert service.price == Decimal("30000")
    assert service.description == "Original"
    log = AuditLog.objects.get(action="servicio.editar")
    assert (log.before["price"], log.after["price"]) == ("25000.00", "30000.00")


# ── Categorías ───────────────────────────────────────────────────────────────


def test_categoria_unica_sin_distinguir_mayusculas(owner):
    services.create_category(owner, name="Cortes")
    with pytest.raises(ValidationError):
        services.create_category(owner, name="CORTES")


def test_borrar_una_categoria_deja_sus_servicios_sin_categoria(owner):
    category = services.create_category(owner, name="Cortes")
    service = _create(owner, category=category.public_id)

    services.soft_delete_category(owner, category.public_id)

    service.refresh_from_db()
    assert service.category is None
    assert list(selectors.list_categories()) == []
    log = AuditLog.objects.get(action="categoria_servicio.eliminar")
    assert log.after["detached_services"] == [str(service.public_id)]
    assert services.create_category(owner, name="Cortes").pk != category.pk


def test_no_se_asigna_una_categoria_de_otra_barberia(member, shop, other_shop):
    with tenant_context(other_shop.pk):
        foreign = services.create_category(member(Role.OWNER, other_shop), name="Ajena")
    with tenant_context(shop.pk), pytest.raises(ValidationError):
        _create(member(Role.OWNER, shop), category=foreign.public_id)


# ── Permisos por rol ─────────────────────────────────────────────────────────


def test_el_administrador_crea_edita_y_desactiva_pero_no_elimina(admin):
    service = _create(admin)
    services.update_service(admin, service.public_id, price=Decimal("1000"))
    services.deactivate_service(admin, service.public_id)
    category = services.create_category(admin, name="Cortes")

    with pytest.raises(PermissionDenied):
        services.soft_delete_service(admin, service.public_id)
    with pytest.raises(PermissionDenied):
        services.soft_delete_category(admin, category.public_id)


def test_el_dueno_elimina(owner):
    service = _create(owner)
    category = services.create_category(owner, name="Cortes")
    assert services.soft_delete_service(owner, service.public_id).is_deleted
    assert services.soft_delete_category(owner, category.public_id).is_deleted


@pytest.mark.parametrize("role", [Role.BARBER, Role.CASHIER, Role.VIEWER])
def test_los_demas_roles_solo_ven(member, in_shop, owner, role):
    service = _create(owner)
    reader = member(role, in_shop)

    with pytest.raises(PermissionDenied):
        _create(reader, name="Otro")
    with pytest.raises(PermissionDenied):
        services.update_service(reader, service.public_id, price=Decimal("1"))
    with pytest.raises(PermissionDenied):
        services.deactivate_service(reader, service.public_id)
    with pytest.raises(PermissionDenied):
        services.soft_delete_service(reader, service.public_id)
    with pytest.raises(PermissionDenied):
        services.create_category(reader, name="Cortes")
    assert list(selectors.list_services()) == [service]


def test_una_membresia_de_otra_barberia_no_escribe_aqui(member, in_shop, other_shop):
    outsider = member(Role.OWNER, other_shop)
    with pytest.raises(PermissionDenied):
        _create(outsider)


def test_una_membresia_inactiva_no_escribe(owner):
    owner.is_active = False
    owner.save()
    with pytest.raises(PermissionDenied):
        _create(owner)


# ── Aislamiento entre barberías (managers) ───────────────────────────────────


def test_cada_barberia_ve_solo_su_catalogo(member, shop, other_shop):
    with tenant_context(shop.pk):
        mine = _create(member(Role.OWNER, shop), name="Corte A")
        services.create_category(member(Role.ADMIN, shop), name="Cortes A")
    with tenant_context(other_shop.pk):
        _create(member(Role.OWNER, other_shop), name="Corte B")

        assert [s.name for s in selectors.list_services()] == ["Corte B"]
        assert list(selectors.list_categories()) == []
        with pytest.raises(Service.DoesNotExist):
            selectors.get_service(mine.public_id)
        with pytest.raises(Service.DoesNotExist):
            services.update_service(member(Role.ADMIN, other_shop), mine.public_id, price=Decimal("1"))


def test_sin_barberia_activa_no_hay_catalogo(member, shop):
    with tenant_context(shop.pk):
        _create(member(Role.OWNER, shop))
    assert list(selectors.list_services()) == []
