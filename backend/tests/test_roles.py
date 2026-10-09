import pytest

from apps.tenancy.roles import ALL_PERMISSIONS, ROLE_PERMISSIONS, Role, role_has_permission


def test_el_dueno_tiene_todos_los_permisos():
    assert ROLE_PERMISSIONS[Role.OWNER] == ALL_PERMISSIONS


@pytest.mark.parametrize(
    "code", ["barberos.eliminar", "servicios.eliminar", "usuarios.eliminar", "barberia.editar", "clientes.anonimizar"]
)
def test_eliminar_catalogo_y_personal_es_exclusivo_del_dueno(code):
    assert role_has_permission(Role.OWNER, code)
    assert not role_has_permission(Role.ADMIN, code)


@pytest.mark.parametrize("code", ["caja.cerrar", "caja.movimiento", "reportes.exportar", "barberos.ver"])
def test_el_barbero_no_maneja_caja_ni_reportes(code):
    assert not role_has_permission(Role.BARBER, code)


def test_el_consultor_solo_lee():
    assert all(code.endswith(".ver") for code in ROLE_PERMISSIONS[Role.VIEWER])


def test_ningun_rol_tiene_permisos_inexistentes():
    for permissions in ROLE_PERMISSIONS.values():
        assert permissions <= ALL_PERMISSIONS


def test_un_permiso_mal_escrito_falla_ruidosamente():
    with pytest.raises(ValueError):
        role_has_permission(Role.OWNER, "caja.borrar")


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.OWNER, True), (Role.ADMIN, True), (Role.CASHIER, True), (Role.BARBER, False), (Role.VIEWER, False)],
)
def test_descontar_en_comandas(role, allowed):
    assert role_has_permission(role, "comandas.descontar") is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.OWNER, True), (Role.ADMIN, True), (Role.CASHIER, False), (Role.BARBER, False), (Role.VIEWER, False)],
)
def test_anular_fiados_es_de_dueno_y_administrador(role, allowed):
    assert role_has_permission(role, "fiados.anular") is allowed


@pytest.mark.parametrize(
    ("role", "allowed"),
    [(Role.OWNER, True), (Role.ADMIN, True), (Role.CASHIER, True), (Role.BARBER, False), (Role.VIEWER, False)],
)
def test_marcar_alertas(role, allowed):
    assert role_has_permission(role, "alertas.marcar") is allowed
