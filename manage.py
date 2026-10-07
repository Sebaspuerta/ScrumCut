#!/usr/bin/env python
import os
import sys


def _load_dotenv_outside_prod() -> None:
    """Carga .env solo con settings de desarrollo o pruebas; producción usa el entorno real."""
    if not os.environ["DJANGO_SETTINGS_MODULE"].endswith((".dev", ".test")):
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    _load_dotenv_outside_prod()
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
