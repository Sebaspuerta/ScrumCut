import pytest

from apps.core.tenant_context import tenant_context
from apps.tenancy.models import Branch

pytestmark = pytest.mark.django_db


def test_cada_barberia_ve_solo_sus_sedes(make_shop):
    a, b = make_shop("a"), make_shop("b")
    with tenant_context(a.pk):
        Branch.objects.create(name="Centro")
    with tenant_context(b.pk):
        Branch.objects.create(name="Norte")

    with tenant_context(a.pk):
        assert list(Branch.objects.values_list("name", flat=True)) == ["Centro"]
    with tenant_context(b.pk):
        assert list(Branch.objects.values_list("name", flat=True)) == ["Norte"]


def test_sin_barberia_activa_no_se_devuelve_nada(make_shop):
    shop = make_shop("a")
    with tenant_context(shop.pk):
        Branch.objects.create(name="Centro")
    assert Branch.objects.count() == 0


def test_no_se_guarda_un_registro_de_negocio_sin_barberia_activa(make_shop):
    make_shop("a")
    with pytest.raises(RuntimeError):
        Branch.objects.create(name="Huérfana")


def test_otra_barberia_no_obtiene_un_objeto_ajeno_por_id(make_shop):
    a, b = make_shop("a"), make_shop("b")
    with tenant_context(a.pk):
        branch = Branch.objects.create(name="Centro")
    with tenant_context(b.pk), pytest.raises(Branch.DoesNotExist):
        Branch.objects.get(pk=branch.pk)
