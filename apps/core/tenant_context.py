"""Barbería activa de la petición o tarea en curso.

Barrera 1 del aislamiento: los managers de negocio leen este valor y filtran.
Barrera 2: en PostgreSQL se fija `app.current_barbershop`, que leen las
políticas Row-Level Security. Ambas se fijan juntas y se limpian juntas.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import connection

_current_barbershop_id: ContextVar[int | None] = ContextVar("current_barbershop_id", default=None)


def get_current_barbershop_id() -> int | None:
    return _current_barbershop_id.get()


def _set_db_setting(barbershop_id: int | None) -> None:
    if connection.vendor != "postgresql":
        return
    value = "" if barbershop_id is None else str(barbershop_id)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_barbershop', %s, false)", [value])


@contextmanager
def tenant_context(barbershop_id: int | None) -> Iterator[None]:
    """Úsalo en vistas, tareas de Celery y comandos que operan sobre una barbería."""
    token = _current_barbershop_id.set(barbershop_id)
    _set_db_setting(barbershop_id)
    try:
        yield
    finally:
        _current_barbershop_id.reset(token)
        _set_db_setting(_current_barbershop_id.get())
