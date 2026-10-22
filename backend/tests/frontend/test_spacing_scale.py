"""Estándar de espacios (docs/diseno.md, "Espacios"): ningún margin, padding ni gap fuera de la escala.

Lee todos los CSS del frontend, resuelve cada variable hasta sus píxeles (con todas sus definiciones,
también las de las media queries) y exige que cada parte del valor sea 0, auto o un paso de la escala.
"""

import re

from django.conf import settings

SCALE = {4, 8, 12, 16, 24, 32, 40, 56, 72}
SPACING = re.compile(r"(?<![\w-])((?:margin|padding|gap|row-gap|column-gap)(?:-[a-z-]+)?)\s*:\s*([^;{}]+);")
CUSTOM = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+);")
PART = re.compile(r"var\([^)]*\)|\S+")
KEYWORDS = {"0", "auto", "inherit"}


def _css() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (settings.FRONTEND_DIR / "static/css").rglob("*.css"))


def _definitions(css: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name, value in CUSTOM.findall(css):
        found.setdefault(name, []).append(value.strip())
    return found


def _pixels(part: str, definitions: dict[str, list[str]]) -> set[int | str]:
    """Los píxeles posibles de una parte del valor; lo que no se puede leer vuelve como texto."""
    if part in KEYWORDS:
        return {0}
    if match := re.fullmatch(r"var\((--[\w-]+)\)", part):
        return {
            pixels
            for value in definitions.get(match.group(1), [part])
            for piece in PART.findall(value)
            for pixels in _pixels(piece, definitions)
        }
    if match := re.fullmatch(r"(\d+)px", part):
        return {int(match.group(1))}
    return {part}


def test_ningun_espacio_sale_de_la_escala():
    css = _css()
    definitions = _definitions(css)
    assert len(SPACING.findall(css)) > 100  # de verdad leyó los archivos
    off_scale = sorted(
        f"{prop}: {value.strip()}"
        for prop, value in SPACING.findall(css)
        if not prop.startswith("--")
        for part in PART.findall(value)
        if _pixels(part, definitions) - SCALE - {0}
    )
    assert off_scale == []


def test_la_escala_se_lee_bien():
    definitions = {"--a": ["var(--b)"], "--b": ["16px", "24px"]}
    assert _pixels("var(--a)", definitions) == {16, 24}
    assert _pixels("calc(1px)", definitions) == {"calc(1px)"}
