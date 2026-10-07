"""Toda tabla de negocio usa por defecto el manager filtrado por barbería.

Django toma por defecto el primer manager declarado en el propio modelo, antes
que los heredados. Si un modelo de negocio declara otro manager (por ejemplo
`todos = models.Manager()`) sin `Meta.default_manager_name = "objects"`, ese pasa
a ser el de por defecto: las validaciones de unicidad y las relaciones inversas
dejarían de filtrar por barbería.
"""

import pytest
from django.apps import apps
from django.db import models
from django.test.utils import isolate_apps

from apps.core.models import TenantManager, TenantScopedModel

TENANT_MODELS = [model for model in apps.get_models() if issubclass(model, TenantScopedModel)]


def _uses_tenant_manager(model) -> bool:
    return isinstance(model._default_manager, TenantManager)


def test_hay_modelos_de_negocio_que_revisar():
    assert len(TENANT_MODELS) >= 3


@pytest.mark.parametrize("model", TENANT_MODELS, ids=lambda model: model._meta.label)
def test_el_manager_por_defecto_filtra_por_barberia(model):
    assert _uses_tenant_manager(model), f"{model._meta.label} usa '{model._default_manager.name}' por defecto"


@isolate_apps("apps.staff")
def test_la_revision_detecta_un_manager_extra_sin_default_manager_name():
    class WithExtraManager(TenantScopedModel):
        everything = models.Manager()

        class Meta:
            app_label = "staff"

    assert not _uses_tenant_manager(WithExtraManager)


@isolate_apps("apps.staff")
def test_default_manager_name_corrige_el_manager_extra():
    class Fixed(TenantScopedModel):
        everything = models.Manager()

        class Meta:
            app_label = "staff"
            default_manager_name = "objects"

    assert _uses_tenant_manager(Fixed)
