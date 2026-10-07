"""Formas canónicas de teléfono, documento y nombre, base de la detección de duplicados (regla 46)."""

import re
import unicodedata

COLOMBIA_PREFIX = "57"


def normalize_phone(raw: str | None) -> str:
    """Solo dígitos. Un número colombiano de 10 dígitos se guarda con el prefijo 57."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        return COLOMBIA_PREFIX + digits
    return digits


def normalize_document(raw: str | None) -> str:
    """Sin espacios, puntos ni guiones, y en mayúsculas: "1.020.304-5" → "10203045"."""
    return re.sub(r"[\s.\-]+", "", raw or "").upper()


def normalize_name(raw: str | None) -> str:
    """Minúsculas, sin tildes y con espacios colapsados, para avisar de posibles duplicados."""
    decomposed = unicodedata.normalize("NFKD", raw or "")
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.lower().split())
