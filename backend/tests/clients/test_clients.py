from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clients import selectors, services
from apps.clients.models import Client
from apps.clients.normalization import normalize_document, normalize_name, normalize_phone
from apps.clients.selectors import ClientStatus, client_status
from apps.core.tenant_context import tenant_context
from apps.tenancy.models import BarbershopSettings
from apps.tenancy.roles import Role

POLICY = "2026-10"
DOCUMENT = "1020304050"


def _create(actor, name="Laura Gómez", force=False, **data) -> Client:
    return services.create_client(
        actor,
        {"full_name": name, **data},
        data_consent_at=timezone.now(),
        data_policy_version=POLICY,
        force=force,
    )


def _duplicate_of(excinfo) -> str:
    error = excinfo.value.error_list[0]
    assert error.code == "duplicate_client"
    return error.params["existing_client"]


@pytest.fixture
def owner(member, in_shop):
    return member(Role.OWNER, in_shop)


# ── Normalización ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("300 123 4567", "573001234567"),
        ("+57 300-123-4567", "573001234567"),
        ("(601) 234 5678", "576012345678"),
        ("12345", "12345"),
        ("", ""),
        (None, ""),
    ],
)
def test_normaliza_el_telefono(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 1020 304a ", "1020304A"),
        ("1.020.304-5", "10203045"),
        ("pa-12.34 x", "PA1234X"),
        (None, ""),
    ],
)
def test_normaliza_el_documento(raw, expected):
    assert normalize_document(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [("  José   PÉREZ ", "jose perez"), ("Ñoño Güiza", "nono guiza"), (None, "")]
)
def test_normaliza_el_nombre(raw, expected):
    assert normalize_name(raw) == expected


@pytest.mark.django_db
def test_documento_con_puntos_es_el_mismo_que_sin_puntos(owner):
    first = _create(owner, document="1.020.304.050")
    with pytest.raises(ValidationError) as excinfo:
        _create(owner, name="Otra", document=DOCUMENT)
    assert _duplicate_of(excinfo) == str(first.public_id)


@pytest.mark.django_db
def test_el_cliente_guarda_los_datos_normalizados(owner):
    client = _create(owner, phone="300 123 4567", email="  Laura@Correo.COM ", document=" 1020 304050 ")
    assert client.phone == "573001234567"
    assert client.email == "laura@correo.com"
    assert client.document_number == DOCUMENT


# ── Documento cifrado ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_el_documento_queda_cifrado_en_la_base_y_se_descifra(owner):
    client = _create(owner, document=DOCUMENT)

    with connection.cursor() as cursor:
        cursor.execute("SELECT row_to_json(c)::text FROM clients_client c WHERE id = %s", [client.pk])
        raw_row = cursor.fetchone()[0]
    assert DOCUMENT not in raw_row
    assert Client.objects.get(pk=client.pk).document_number == DOCUMENT


@pytest.mark.django_db
def test_quitar_el_documento_borra_cifrado_y_huella(owner):
    client = _create(owner, document=DOCUMENT)
    services.update_client(owner, client.public_id, {"document": ""})
    client.refresh_from_db()
    assert (client.document_number, client.document_number_encrypted, client.document_hash) == ("", "", "")


@pytest.mark.django_db
def test_la_auditoria_no_guarda_el_documento_en_claro(owner):
    client = _create(owner, document=DOCUMENT)
    services.update_client(owner, client.public_id, {"document": "99887766"})
    services.update_client(owner, client.public_id, {"full_name": "Laura G."})

    logs = {log.action: log for log in AuditLog.objects.all()}
    for log in AuditLog.objects.all():
        assert DOCUMENT not in str(log.before) + str(log.after)
        assert "99887766" not in str(log.before) + str(log.after)
    assert logs["cliente.crear"].after["has_document"] is True
    edits = list(AuditLog.objects.filter(action="cliente.editar").order_by("pk"))
    assert edits[0].after["document_changed"] is True
    assert "document_changed" not in edits[1].after


# ── Regla 46: duplicados ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_telefono_duplicado_en_otro_formato_falla_con_el_existente(owner):
    first = _create(owner, phone="3001234567")
    with pytest.raises(ValidationError) as excinfo:
        _create(owner, name="Otra", phone="+57 300 123 4567")
    assert _duplicate_of(excinfo) == str(first.public_id)


@pytest.mark.django_db
def test_documento_duplicado_con_espacios_y_minusculas_falla(owner):
    first = _create(owner, document="ab 123")
    with pytest.raises(ValidationError) as excinfo:
        _create(owner, name="Otra", document="AB123")
    assert _duplicate_of(excinfo) == str(first.public_id)


@pytest.mark.django_db
def test_force_no_duplica_telefono_ni_documento_exactos(owner):
    first = _create(owner, phone="3001234567", document=DOCUMENT)
    for data in ({"phone": "3001234567"}, {"document": DOCUMENT}):
        with pytest.raises(ValidationError) as excinfo:
            _create(owner, name="Forzada", force=True, **data)
        assert _duplicate_of(excinfo) == str(first.public_id)
    assert Client.objects.count() == 1


@pytest.mark.django_db
def test_editar_hacia_el_telefono_de_otro_falla(owner):
    first = _create(owner, phone="3001234567")
    second = _create(owner, name="Otra", phone="3110000000")
    with pytest.raises(ValidationError) as excinfo:
        services.update_client(owner, second.public_id, {"phone": "300 123 4567"})
    assert _duplicate_of(excinfo) == str(first.public_id)


@pytest.mark.django_db
def test_sin_telefono_ni_documento_no_hay_duplicado(owner):
    _create(owner, name="Sin datos 1")
    _create(owner, name="Sin datos 2")
    assert Client.objects.count() == 2


@pytest.mark.django_db
def test_un_cliente_borrado_libera_telefono_y_documento(owner):
    first = _create(owner, phone="3001234567", document=DOCUMENT)
    services.soft_delete_client(owner, first.public_id)
    assert _create(owner, name="Nueva", phone="3001234567", document=DOCUMENT).pk != first.pk


@pytest.mark.django_db
def test_find_duplicate_normaliza_lo_que_recibe(owner):
    first = _create(owner, phone="3001234567", document=DOCUMENT)
    assert selectors.find_duplicate("+57 300 123 4567", None) == first
    assert selectors.find_duplicate(None, " 1020 304050") == first
    assert selectors.find_duplicate("3110000000", "otro") is None
    assert selectors.find_duplicate("3001234567", None, exclude=first) is None


# ── Autorización de datos (Ley 1581) ─────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "consent",
    [None, timezone.now() + timedelta(days=1), datetime(2026, 1, 1, 9, 0)],  # la última, sin zona a propósito
    ids=["sin_autorizacion", "futura", "sin_zona_horaria"],
)
def test_crear_sin_autorizacion_valida_falla(owner, consent):
    with pytest.raises(ValidationError):
        services.create_client(owner, {"full_name": "Laura"}, data_consent_at=consent, data_policy_version=POLICY)
    assert Client.objects.count() == 0


@pytest.mark.django_db
def test_la_version_de_la_politica_es_obligatoria(owner):
    with pytest.raises(ValidationError):
        services.create_client(owner, {"full_name": "Laura"}, data_consent_at=timezone.now(), data_policy_version=" ")


# ── Estado del cliente (regla 47, pura) ──────────────────────────────────────

NOW = timezone.now()
RECENT = NOW - timedelta(days=5)


@pytest.mark.parametrize(
    ("visits", "spent", "last_visit", "balance", "expected"),
    [
        (5, Decimal("50000"), RECENT, Decimal("1000"), ClientStatus.DEBTOR),
        (0, Decimal("0"), None, Decimal("0"), ClientStatus.NEW),
        (2, Decimal("40000"), RECENT, Decimal("0"), ClientStatus.NEW),
        (3, Decimal("60000"), RECENT, Decimal("0"), ClientStatus.FREQUENT),
        (2, Decimal("200000"), RECENT, Decimal("0"), ClientStatus.VIP),
        (10, Decimal("100000"), RECENT, Decimal("0"), ClientStatus.VIP),
        (12, Decimal("500000"), NOW - timedelta(days=91), Decimal("0"), ClientStatus.INACTIVE),
        (12, Decimal("500000"), NOW - timedelta(days=91), Decimal("1"), ClientStatus.DEBTOR),
        (3, Decimal("60000"), NOW - timedelta(days=90), Decimal("0"), ClientStatus.FREQUENT),
    ],
)
def test_estado_con_umbrales_por_defecto(visits, spent, last_visit, balance, expected):
    assert client_status(visits, spent, last_visit, balance, BarbershopSettings(), now=NOW) == expected


def test_estado_con_umbrales_personalizados():
    custom = BarbershopSettings(
        vip_min_spent=Decimal("100000"), vip_min_visits=6, frequent_min_visits=2, inactive_after_days=30
    )
    assert client_status(2, Decimal("40000"), RECENT, Decimal("0"), custom, now=NOW) == ClientStatus.FREQUENT
    assert client_status(2, Decimal("100000"), RECENT, Decimal("0"), custom, now=NOW) == ClientStatus.VIP
    assert client_status(6, Decimal("0"), RECENT, Decimal("0"), custom, now=NOW) == ClientStatus.VIP
    old = NOW - timedelta(days=31)
    assert client_status(6, Decimal("0"), old, Decimal("0"), custom, now=NOW) == ClientStatus.INACTIVE


@pytest.mark.django_db
def test_cada_barberia_nace_con_su_configuracion_por_defecto(shop):
    with tenant_context(shop.pk):
        settings = BarbershopSettings.objects.get()
    assert settings.barbershop == shop
    assert (settings.vip_min_spent, settings.vip_min_visits) == (Decimal("200000"), 10)
    assert (settings.frequent_min_visits, settings.inactive_after_days) == (3, 90)


# ── Búsqueda ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_busqueda_por_nombre_telefono_y_documento(owner):
    laura = _create(owner, name="Laura Gómez", phone="3001234567", document=DOCUMENT)
    _create(owner, name="Pedro Ruiz", phone="3110000000")

    assert list(selectors.list_clients(owner, "laura")) == [laura]
    assert list(selectors.list_clients(owner, "300 123")) == [laura]
    assert list(selectors.list_clients(owner, "1020 304050")) == [laura]
    assert [c.full_name for c in selectors.list_clients(owner)] == ["Laura Gómez", "Pedro Ruiz"]
    assert list(selectors.list_clients(owner, "nadie")) == []


# ── Permisos ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.ADMIN, Role.BARBER, Role.CASHIER])
def test_crean_y_editan_pero_solo_el_dueno_elimina(member, in_shop, owner, role):
    actor = member(role, in_shop)
    client = _create(actor, phone="3001234567")
    services.update_client(actor, client.public_id, {"notes": "Prefiere tijera"})
    with pytest.raises(PermissionDenied):
        services.soft_delete_client(actor, client.public_id)
    assert services.soft_delete_client(owner, client.public_id).is_deleted


@pytest.mark.django_db
def test_el_consultor_solo_lee(member, in_shop, owner):
    client = _create(owner)
    viewer = member(Role.VIEWER, in_shop)
    with pytest.raises(PermissionDenied):
        _create(viewer, name="Otra")
    with pytest.raises(PermissionDenied):
        services.update_client(viewer, client.public_id, {"notes": "x"})
    assert selectors.get_client(viewer, client.public_id) == client
    assert list(selectors.list_clients(viewer)) == [client]


@pytest.mark.django_db
def test_una_membresia_de_otra_barberia_no_lee_ni_escribe(member, in_shop, other_shop):
    outsider = member(Role.OWNER, other_shop)
    with pytest.raises(PermissionDenied):
        _create(outsider)
    with pytest.raises(PermissionDenied):
        selectors.list_clients(outsider)


# ── Aislamiento entre barberías ──────────────────────────────────────────────


@pytest.mark.django_db
def test_cada_barberia_ve_solo_sus_clientes_y_puede_repetir_telefono(member, shop, other_shop):
    with tenant_context(shop.pk):
        mine = _create(member(Role.OWNER, shop), phone="3001234567", document=DOCUMENT)
    with tenant_context(other_shop.pk):
        theirs = member(Role.OWNER, other_shop)
        _create(theirs, name="Mismo teléfono", phone="3001234567", document=DOCUMENT)

        assert [c.full_name for c in selectors.list_clients(theirs)] == ["Mismo teléfono"]
        with pytest.raises(Client.DoesNotExist):
            selectors.get_client(theirs, mine.public_id)
        with pytest.raises(Client.DoesNotExist):
            services.update_client(theirs, mine.public_id, {"notes": "x"})


# ── Posibles duplicados por nombre ───────────────────────────────────────────


@pytest.mark.django_db
def test_mismo_nombre_normalizado_avisa_y_force_lo_confirma(owner):
    first = _create(owner, name="José Pérez", phone="3001234567")
    with pytest.raises(ValidationError) as excinfo:
        _create(owner, name="  jose   PEREZ ", phone="3110000000")
    error = excinfo.value.error_list[0]
    assert error.code == "possible_duplicate"
    assert error.params["possible_duplicates"] == [str(first.public_id)]

    second = _create(owner, name="  jose   PEREZ ", phone="3110000000", force=True)
    assert second.pk != first.pk


@pytest.mark.django_db
def test_force_no_salta_el_duplicado_exacto_aunque_el_nombre_coincida(owner):
    first = _create(owner, name="José Pérez", phone="3001234567")
    with pytest.raises(ValidationError) as excinfo:
        _create(owner, name="José Pérez", phone="300 123 4567", force=True)
    assert _duplicate_of(excinfo) == str(first.public_id)


@pytest.mark.django_db
def test_borrados_y_anonimizados_no_cuentan_como_posibles_duplicados(owner):
    deleted = _create(owner, name="José Pérez")
    services.soft_delete_client(owner, deleted.public_id)
    anonymized = _create(owner, name="Ana Ruiz")
    services.anonymize_client(owner, anonymized.public_id)

    assert _create(owner, name="José Pérez").pk
    assert _create(owner, name="Ana Ruiz").pk


# ── Anonimización (Ley 1581) ─────────────────────────────────────────────────


@pytest.mark.django_db
def test_anonimizar_borra_los_datos_personales_y_conserva_el_registro(owner):
    client = _create(
        owner,
        name="Laura Gómez",
        phone="3001234567",
        email="laura@correo.com",
        document=DOCUMENT,
        birth_date=datetime(1995, 4, 12).date(),
        notes="Alérgica al alcohol",
    )
    pk, public_id, consent = client.pk, client.public_id, client.data_consent_at

    services.anonymize_client(owner, public_id)

    client = Client.objects.get(pk=pk)
    assert client.public_id == public_id and not client.is_deleted
    assert client.full_name == services.ANONYMIZED_NAME
    assert (client.phone, client.email, client.notes, client.name_key) == ("", "", "", "")
    assert (client.document_number_encrypted, client.document_hash, client.birth_date) == ("", "", None)
    assert client.is_anonymized
    assert client.data_consent_at == consent  # la prueba del consentimiento se conserva


@pytest.mark.django_db
def test_la_auditoria_de_la_anonimizacion_no_tiene_datos_personales(owner):
    client = _create(owner, name="Laura Gómez", phone="3001234567", document=DOCUMENT)
    services.anonymize_client(owner, client.public_id)
    log = AuditLog.objects.get(action="cliente.anonimizar")
    text = str(log.before) + str(log.after)
    for personal in ("Laura", "3001234567", DOCUMENT):
        assert personal not in text
    assert set(log.after) == {"anonymized_at"}


@pytest.mark.django_db
def test_anonimizar_es_irreversible(owner):
    client = _create(owner)
    services.anonymize_client(owner, client.public_id)
    with pytest.raises(ValidationError):
        services.anonymize_client(owner, client.public_id)
    with pytest.raises(ValidationError):
        services.update_client(owner, client.public_id, {"full_name": "Laura otra vez"})


@pytest.mark.django_db
def test_un_anonimizado_sale_de_las_listas_pero_sigue_disponible_para_el_historial(owner):
    client = _create(owner, phone="3001234567")
    services.anonymize_client(owner, client.public_id)
    assert list(selectors.list_clients(owner)) == []
    assert selectors.get_client(owner, client.public_id).is_anonymized
    assert _create(owner, name="Nueva", phone="3001234567").pk  # su teléfono quedó libre


@pytest.mark.django_db
def test_se_anonimiza_tambien_un_cliente_borrado(owner):
    client = _create(owner, phone="3001234567")
    services.soft_delete_client(owner, client.public_id)
    assert services.anonymize_client(owner, client.public_id).is_anonymized


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.ADMIN, Role.CASHIER, Role.BARBER, Role.VIEWER])
def test_solo_el_dueno_anonimiza(member, in_shop, owner, role):
    client = _create(owner)
    with pytest.raises(PermissionDenied):
        services.anonymize_client(member(role, in_shop), client.public_id)
    client.refresh_from_db()
    assert not client.is_anonymized
