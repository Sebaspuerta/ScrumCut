"""Estándar de espacios (docs/diseno/identidad-r1.md, "Espacios"): ningún margin, padding ni gap fuera de la escala.

Lee el CSS de las pantallas de Django (frontend/static/css) y el de la app de React (frontend/app/src),
resuelve cada variable hasta sus píxeles (con todas sus definiciones, también las de las media queries)
y exige que cada parte del valor sea 0, auto o un paso de la escala.
"""

import re
from pathlib import Path

from django.conf import settings

SCALE = {4, 8, 12, 16, 24, 32, 40, 56, 72}
CSS_ROOTS = ("static/css", "app/src")
SPACING = re.compile(r"(?<![\w-])((?:margin|padding|gap|row-gap|column-gap)(?:-[a-z-]+)?)\s*:\s*([^;{}]+);")
CUSTOM = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+);")
PART = re.compile(r"calc\((?:[^()]|\([^()]*\))*\)|var\([^)]*\)|\S+")
CALC_TERM = re.compile(r"var\([^)]*\)|[^\s+()]+")
KEYWORDS = {"0", "auto", "inherit"}
# Medidas del marco fijo de la app de React: el contenido empieza donde terminan la barra superior y la
# lateral. Solo valen sumadas a un paso de la escala dentro de un calc(), o solas como desplazamiento.
FRAME = {"--topbar-height", "--sidebar-width"}
# Lo que no es un espacio entre elementos, con su motivo.
EXCEPTIONS = {
    ("app/src/ui/Dialog.module.css", "padding-top: 12vh"): "el diálogo se ubica según el alto de la ventana",
}


def _files() -> list[Path]:
    return [path for root in CSS_ROOTS for path in (settings.FRONTEND_DIR / root).rglob("*.css")]


def _definitions(css: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name, value in CUSTOM.findall(css):
        found.setdefault(name, []).append(value.strip())
    return found


def _pixels(part: str, definitions: dict[str, list[str]]) -> set[int | str]:
    """Los píxeles posibles de una parte del valor; lo que no se puede leer vuelve como texto."""
    if part in KEYWORDS:
        return {0}
    if part.startswith("calc("):
        terms = CALC_TERM.findall(part.removeprefix("calc"))
        return {pixels for term in terms for pixels in _pixels(term, definitions)}
    if match := re.fullmatch(r"var\((--[\w-]+)\)", part):
        if match.group(1) in FRAME:
            return {0}
        return {
            pixels
            for value in definitions.get(match.group(1), [part])
            for piece in PART.findall(value)
            for pixels in _pixels(piece, definitions)
        }
    if match := re.fullmatch(r"(\d+)px", part):
        return {int(match.group(1))}
    return {part}


def _off_scale(name: str, css: str, definitions: dict[str, list[str]]) -> list[str]:
    return [
        f"{name}: {prop}: {value.strip()}"
        for prop, value in SPACING.findall(css)
        if not prop.startswith("--")
        and (name, f"{prop}: {value.strip()}") not in EXCEPTIONS
        and any(_pixels(part, definitions) - SCALE - {0} for part in PART.findall(value))
    ]


def test_ningun_espacio_sale_de_la_escala():
    sheets = {path.relative_to(settings.FRONTEND_DIR).as_posix(): path.read_text(encoding="utf-8") for path in _files()}
    css = "\n".join(sheets.values())
    definitions = _definitions(css)
    assert len(SPACING.findall(css)) > 300  # de verdad leyó los dos frontends
    assert {name.split("/")[0] for name in sheets} == {"static", "app"}
    off_scale = sorted(line for name, sheet in sheets.items() for line in _off_scale(name, sheet, definitions))
    assert off_scale == []


def test_las_excepciones_siguen_existiendo():
    for name, declaration in EXCEPTIONS:
        assert declaration in (settings.FRONTEND_DIR / name).read_text(encoding="utf-8"), name


def test_la_escala_se_lee_bien():
    definitions = {"--a": ["var(--b)"], "--b": ["16px", "24px"], "--topbar-height": ["64px"]}
    assert _pixels("var(--a)", definitions) == {16, 24}
    assert _pixels("calc(var(--topbar-height) + var(--a))", definitions) == {0, 16, 24}
    assert _pixels("calc(var(--topbar-height) + 5px)", definitions) == {0, 5}
    assert _pixels("12vh", definitions) == {"12vh"}
