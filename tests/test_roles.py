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
