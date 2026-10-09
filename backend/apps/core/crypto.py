"""Cifrado de campos personales y huellas para buscarlos sin descifrar.

- `encrypt`/`decrypt`: Fernet (AES-128-CBC + HMAC) con `FIELD_ENCRYPTION_KEY`.
- `keyed_hash`: HMAC-SHA256 con `FIELD_HASH_KEY`. Determinista, para unicidad y
  búsqueda exacta; sin la clave no se puede probar documento por documento.

Las claves vienen del entorno (`config.env.require`). Rotar cualquiera exige
recalcular los datos guardados.
"""

import hashlib
import hmac
from functools import cache

from cryptography.fernet import Fernet
from django.conf import settings


@cache
def _fernet() -> Fernet:
    return Fernet(settings.FIELD_ENCRYPTION_KEY)


def validate_keys() -> None:
    """Falla al arrancar si la clave de cifrado no tiene formato Fernet."""
    _fernet()


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def keyed_hash(value: str) -> str:
    return hmac.new(settings.FIELD_HASH_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()
