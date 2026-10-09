#!/usr/bin/env python
import os
import sys

from config.env import load_local_dotenv


def _load_dotenv_outside_prod() -> None:
    """Carga .env solo con settings de desarrollo o pruebas; producción usa el entorno real."""
    if os.environ["DJANGO_SETTINGS_MODULE"].endswith((".dev", ".test")):
        load_local_dotenv()


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    _load_dotenv_outside_prod()
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
