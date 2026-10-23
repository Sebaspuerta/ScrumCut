"""Lector del manifest de Vite: qué archivos compilados de la app de React (frontend/app) carga su página.

`vite build` deja los archivos en frontend/static/app/ con su `manifest.json`; Django los sirve como estáticos.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static

STATIC_PREFIX = "app/"  # la carpeta de la compilación dentro de los estáticos (base de vite.config.ts)
NOT_BUILT = "Falta compilar la app de React: npm run build en frontend/app."


@dataclass(frozen=True)
class ViteEntry:
    script: str
    styles: tuple[str, ...]


def _load(manifest_path: Path) -> dict:
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ImproperlyConfigured(NOT_BUILT) from exc


def _styles(manifest: dict, key: str, seen: set[str]) -> list[str]:
    """Los CSS de los fragmentos que importa y luego los suyos, en el orden en que Vite los enlaza."""
    if key in seen:
        return []
    seen.add(key)
    chunk = manifest[key]
    imported = [css for child in chunk.get("imports", []) for css in _styles(manifest, child, seen)]
    return imported + chunk.get("css", [])


def read_entry(manifest_path: Path, entry: str) -> ViteEntry:
    """El script de la entrada y sus hojas de estilo, como URL de estáticos. Sin compilar, ImproperlyConfigured."""
    manifest = _load(manifest_path)
    if entry not in manifest:
        raise ImproperlyConfigured(NOT_BUILT)
    styles = _styles(manifest, entry, set())
    return ViteEntry(
        script=static(STATIC_PREFIX + manifest[entry]["file"]),
        styles=tuple(static(STATIC_PREFIX + css) for css in dict.fromkeys(styles)),
    )
