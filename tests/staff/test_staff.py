from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.catalog.models import Service
from apps.core.tenant_context import tenant_context
from apps.staff import selectors, services
from apps.staff.models import Barber, CommissionRule, CommissionType
from apps.tenancy.models import Branch
from apps.tenancy.roles import Role

pytestmark = pytest.mark.django_db

PCT = CommissionType.PERCENTAGE
FIXED = CommissionType.FIXED


def _create(actor, name="Ana", commission_type=PCT, value=Decimal("40"), **data) -> Barber:
    return services.create_barber(actor, {"display_name": name, **data}, commission_type, value)


def _service(name="Corte") -> Service:
    return Service.objects.create(name=name, price=Decimal("25000"), duration_minutes=30)


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)


@pytest.fixture
def admin(member, in_shop):
    return member(Role.ADMIN, in_shop)


# ── Alta y comisión inicial ──────────────────────────────────────────────────


def test_crear_barbero_crea_su_regla_general_vigente_desde_ahora(owner):
    barber = _create(owner, name="  Ana  ", phone="3000000000")

    assert barber.display_name == "Ana"
    rule = barber.commission_rules.get()
    assert (rule.service, rule.commission_type, rule.value) == (None, PCT, Decimal("40"))
    assert rule.valid_from <= timezone.now()
    assert selectors.resolve_commission(barber, None, timezone.now()) == (PCT, Decimal("40.00"))
    log = AuditLog.objects.get(action="barbero.crear")
    assert log.after["commission"]["value"] == "40.00"


def test_una_comision_invalida_no_deja_barbero_a_medias(owner):
    with pytest.raises(ValidationError):
        _create(owner, value=Decimal("101"))
    assert Barber.objects.count() == 0
    assert CommissionRule.objects.count() == 0


# ── Regla 41: una membresía, un barbero ──────────────────────────────────────


def test_se_vincula_una_membresia_de_barbero(owner, member, in_shop):
    login = member(Role.BARBER, in_shop)
    barber = _create(owner, membership=login.public_id)
    assert barber.membership == login


def test_una_membresia_no_se_vincula_a_dos_barberos(owner, member, in_shop):
    login = member(Role.BARBER, in_shop)
    _create(owner, name="Ana", membership=login.public_id)
    other = _create(owner, name="Beto")

    with pytest.raises(ValidationError):
        _create(owner, name="Caro", membership=login.public_id)
    with pytest.raises(ValidationError):
        services.update_barber(owner, other.public_id, {"membership": login.public_id})


def test_desvincular_libera_la_membresia(owner, member, in_shop):
    login = member(Role.BARBER, in_shop)
    ana = _create(owner, name="Ana", membership=login.public_id)
    services.update_barber(owner, ana.public_id, {"membership": None})
    assert _create(owner, name="Beto", membership=login.public_id).membership == login


def test_un_barbero_borrado_conserva_su_membresia(owner, member, in_shop):
    login = member(Role.BARBER, in_shop)
    ana = _create(owner, name="Ana", membership=login.public_id)
    services.soft_delete_barber(owner, ana.public_id)
    with pytest.raises(ValidationError):
        _create(owner, name="Beto", membership=login.public_id)


@pytest.mark.parametrize("case", ["otra_barberia", "inactiva", "rol_cajero"])
def test_membresias_que_no_se_pueden_vincular(owner, member, in_shop, other_shop, case):
    if case == "otra_barberia":
        login = member(Role.BARBER, other_shop)
    elif case == "inactiva":
        login = member(Role.BARBER, in_shop)
        login.is_active = False
        login.save()
    else:
        login = member(Role.CASHIER, in_shop)
    with pytest.raises(ValidationError):
        _create(owner, membership=login.public_id)


# ── Regla 42: el barbero del dueño no se borra ───────────────────────────────


def test_no_se_borra_el_barbero_vinculado_al_dueno(owner, member, in_shop):
    login = member(Role.BARBER, in_shop)
    barber = _create(owner, membership=login.public_id)
    login.role = Role.OWNER
    login.save()

    with pytest.raises(ValidationError):
        services.soft_delete_barber(owner, barber.public_id)
    barber.refresh_from_db()
    assert not barber.is_deleted


def test_el_dueno_borra_un_barbero_y_desaparece(owner):
    barber = _create(owner)
    services.soft_delete_barber(owner, barber.public_id)

    assert list(selectors.list_barbers(owner, active_only=False)) == []
    assert selectors.list_active_barbers_basic(owner) == []
    with pytest.raises(Barber.DoesNotExist):
        selectors.get_barber(owner, barber.public_id)
    with pytest.raises(Barber.DoesNotExist):
        services.update_barber(owner, barber.public_id, {"phone": "1"})
    assert AuditLog.objects.get(action="barbero.eliminar").after["deleted_at"] is not None


def test_desactivar_y_activar(owner):
    barber = _create(owner)
    services.deactivate_barber(owner, barber.public_id)
    assert list(selectors.list_barbers(owner)) == []
    assert list(selectors.list_barbers(owner, active_only=False)) == [barber]
    assert selectors.list_active_barbers_basic(owner) == []

    services.activate_barber(owner, barber.public_id)
    assert list(selectors.list_barbers(owner)) == [barber]


# ── Historial de comisiones (decisión 3, defecto 1) ──────────────────────────


def test_cambiar_la_comision_no_altera_lo_resuelto_para_una_fecha_pasada(owner):
    barber = _create(owner, value=Decimal("40"))
    before_change = timezone.now()
    starts = before_change + timedelta(days=1)

    services.set_commission(owner, barber.public_id, PCT, Decimal("50"), valid_from=starts)

    assert selectors.resolve_commission(barber, None, before_change) == (PCT, Decimal("40.00"))
    assert selectors.resolve_commission(barber, None, starts + timedelta(hours=1)) == (PCT, Decimal("50.00"))
    assert sorted(barber.commission_rules.values_list("value", flat=True)) == [Decimal("40"), Decimal("50")]


def test_sin_fecha_la_regla_nueva_vale_desde_ahora(owner):
    barber = _create(owner)
    rule = services.set_commission(owner, barber.public_id, FIXED, Decimal("5000"))
    assert rule.valid_from <= timezone.now()
    assert selectors.resolve_commission(barber, None, timezone.now()) == (FIXED, Decimal("5000.00"))
    assert AuditLog.objects.get(action="comision.crear").after["value"] == "5000.00"


@pytest.mark.parametrize(
    "valid_from",
    [timezone.now() - timedelta(days=1), datetime(2030, 1, 1, 8, 0)],  # la segunda, sin zona a propósito
    ids=["pasada", "sin_zona_horaria"],
)
def test_no_se_aceptan_vigencias_pasadas_ni_sin_zona(owner, valid_from):
    barber = _create(owner)
    with pytest.raises(ValidationError):
        services.set_commission(owner, barber.public_id, PCT, Decimal("10"), valid_from=valid_from)


def test_la_regla_del_servicio_gana_sobre_la_general(owner):
    barber = _create(owner, value=Decimal("40"))
    corte, barba = _service("Corte"), _service("Barba")
    services.set_commission(owner, barber.public_id, FIXED, Decimal("8000"), service=corte.public_id)
    now = timezone.now()

    assert selectors.resolve_commission(barber, corte, now) == (FIXED, Decimal("8000.00"))
    assert selectors.resolve_commission(barber, barba, now) == (PCT, Decimal("40.00"))
    assert selectors.resolve_commission(barber, None, now) == (PCT, Decimal("40.00"))


def test_sin_reglas_la_comision_es_cero(in_shop):
    barber = Barber.objects.create(display_name="Sin reglas")
    assert selectors.resolve_commission(barber, None, timezone.now()) == (PCT, Decimal("0"))


@pytest.mark.parametrize(
    ("commission_type", "value", "valid"),
    [(PCT, Decimal("100"), True), (PCT, Decimal("100.01"), False), (FIXED, Decimal("150000"), True), (PCT, -1, False)],
)
def test_limites_del_valor_de_comision(owner, commission_type, value, valid):
    barber = _create(owner)
    if valid:
        services.set_commission(owner, barber.public_id, commission_type, value)
    else:
        with pytest.raises(ValidationError):
            services.set_commission(owner, barber.public_id, commission_type, value)


def test_una_regla_de_comision_no_se_edita_ni_se_borra(owner):
    rule = _create(owner).commission_rules.get()

    rule.value = Decimal("1")
    with pytest.raises(PermissionError):
        rule.save()
    with pytest.raises(PermissionError):
        rule.delete()
    with pytest.raises(PermissionError):
        CommissionRule.objects.filter(pk=rule.pk).update(value=Decimal("1"))
    with pytest.raises(PermissionError):
        CommissionRule.objects.filter(pk=rule.pk).delete()
    assert CommissionRule.objects.get(pk=rule.pk).value == Decimal("40")


# ── Permisos por rol ─────────────────────────────────────────────────────────


def test_el_administrador_gestiona_pero_no_elimina(admin):
    barber = _create(admin)
    services.update_barber(admin, barber.public_id, {"alias": "La rápida"})
    services.deactivate_barber(admin, barber.public_id)
    services.set_commission(admin, barber.public_id, PCT, Decimal("45"))
    with pytest.raises(PermissionDenied):
        services.soft_delete_barber(admin, barber.public_id)


@pytest.mark.parametrize("role", [Role.BARBER, Role.CASHIER, Role.VIEWER])
def test_los_demas_roles_no_escriben(member, in_shop, owner, role):
    barber = _create(owner)
    actor = member(role, in_shop)
    with pytest.raises(PermissionDenied):
        _create(actor, name="Otro")
    with pytest.raises(PermissionDenied):
        services.update_barber(actor, barber.public_id, {"phone": "1"})
    with pytest.raises(PermissionDenied):
        services.set_commission(actor, barber.public_id, PCT, Decimal("99"))
    with pytest.raises(PermissionDenied):
        services.soft_delete_barber(actor, barber.public_id)


@pytest.mark.parametrize(("role", "can_list"), [(Role.VIEWER, True), (Role.BARBER, False), (Role.CASHIER, False)])
def test_la_lista_completa_exige_barberos_ver(member, in_shop, owner, role, can_list):
    barber = _create(owner)
    reader = member(role, in_shop)
    if can_list:
        assert list(selectors.list_barbers(reader)) == [barber]
        assert selectors.get_barber(reader, barber.public_id) == barber
    else:
        with pytest.raises(PermissionDenied):
            selectors.list_barbers(reader)
        with pytest.raises(PermissionDenied):
            selectors.get_barber(reader, barber.public_id)


# ── Regla 45: lista básica ───────────────────────────────────────────────────


@pytest.mark.parametrize("role", [Role.BARBER, Role.CASHIER, Role.VIEWER])
def test_la_lista_basica_solo_expone_identificador_y_nombre(member, in_shop, owner, role):
    _create(owner, name="Ana", phone="3000000000", notes="Privado")
    inactive = _create(owner, name="Beto")
    services.deactivate_barber(owner, inactive.public_id)

    rows = selectors.list_active_barbers_basic(member(role, in_shop))

    assert [row["display_name"] for row in rows] == ["Ana"]
    assert set(rows[0]) == {"public_id", "display_name"}


def test_la_lista_basica_exige_una_membresia_activa_de_esta_barberia(member, in_shop, other_shop):
    outsider = member(Role.OWNER, other_shop)
    with pytest.raises(PermissionDenied):
        selectors.list_active_barbers_basic(outsider)

    inactive = member(Role.BARBER, in_shop)
    inactive.is_active = False
    inactive.save()
    with pytest.raises(PermissionDenied):
        selectors.list_active_barbers_basic(inactive)


def test_una_membresia_de_otra_barberia_no_escribe_aqui(member, in_shop, other_shop):
    with pytest.raises(PermissionDenied):
        _create(member(Role.OWNER, other_shop))


# ── Aislamiento entre barberías ──────────────────────────────────────────────


def test_cada_barberia_ve_solo_su_personal(member, shop, other_shop):
    with tenant_context(shop.pk):
        mine = _create(member(Role.OWNER, shop), name="Ana")
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        _create(theirs, name="Beto")

        assert [b.display_name for b in selectors.list_barbers(theirs)] == ["Beto"]
        assert [r["display_name"] for r in selectors.list_active_barbers_basic(theirs)] == ["Beto"]
        with pytest.raises(Barber.DoesNotExist):
            selectors.get_barber(theirs, mine.public_id)
        with pytest.raises(Barber.DoesNotExist):
            services.set_commission(theirs, mine.public_id, PCT, Decimal("99"))
        # Fuera de su barbería, las reglas de Ana no son visibles: falla cerrado.
        assert selectors.resolve_commission(mine, None, timezone.now()) == (PCT, Decimal("0"))


def test_no_se_usan_sedes_ni_servicios_de_otra_barberia(member, shop, other_shop):
    with tenant_context(other_shop.pk):
        foreign_branch = Branch.objects.create(name="Ajena")
        foreign_service = _service("Ajeno")
    with tenant_context(shop.pk):
        owner = member(Role.OWNER, shop)
        with pytest.raises(ValidationError):
            _create(owner, branch=foreign_branch.public_id)
        barber = _create(owner, branch=Branch.objects.create(name="Centro").public_id)
        assert barber.branch.name == "Centro"
        with pytest.raises(ValidationError):
            services.set_commission(owner, barber.public_id, FIXED, Decimal("1"), service=foreign_service.public_id)
