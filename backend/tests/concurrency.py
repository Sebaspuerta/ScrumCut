"""Apoyo para las pruebas de concurrencia: ningún hilo deja la suite colgada."""

import threading

import pytest

THREAD_TIMEOUT_S = 15


def run_threads(threads: list[threading.Thread]) -> None:
    """Arranca los hilos y espera a cada uno; si alguno sigue vivo, la prueba falla."""
    for thread in threads:
        thread.daemon = True  # un hilo trabado no impide que el proceso de pytest termine
        thread.start()
    for thread in threads:
        thread.join(timeout=THREAD_TIMEOUT_S)
    stuck = [thread.name for thread in threads if thread.is_alive()]
    if stuck:
        pytest.fail(
            f"{len(stuck)} hilo(s) siguen vivos tras {THREAD_TIMEOUT_S} s: posible bloqueo ({', '.join(stuck)})."
        )
