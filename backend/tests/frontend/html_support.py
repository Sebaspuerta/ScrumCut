"""Lectura de HTML renderizado para las pruebas de la interfaz, con la biblioteca estándar."""

from html.parser import HTMLParser

VOID_TAGS = {"input", "img", "link", "meta", "br", "hr", "source", "path", "circle", "rect", "line", "polyline"}

Ancestors = tuple[tuple[str, str | None], ...]  # (etiqueta, id) de cada ancestro


class _Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict, Ancestors]] = []
        self._stack: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes, tuple(self._stack)))
        if tag not in VOID_TAGS:
            self._stack.append((tag, attributes.get("id")))

    def handle_endtag(self, tag):
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break


def elements(html: str) -> list[tuple[str, dict, Ancestors]]:
    parser = _Elements()
    parser.feed(html)
    return parser.elements


def inside(html: str, container_id: str, tag: str) -> list[dict]:
    """Atributos de cada `tag` que está dentro del elemento con ese `id`."""
    return [
        attrs
        for name, attrs, ancestors in elements(html)
        if name == tag and container_id in {element_id for _, element_id in ancestors}
    ]


def forms(html: str) -> list[dict]:
    """Cada formulario con su método, su acción y los nombres de los campos que contiene."""
    found = []
    for tag, attrs, ancestors in elements(html):
        if tag == "form":
            found.append({"method": attrs.get("method", "get").lower(), "action": attrs.get("action"), "fields": []})
        elif tag == "input" and found and "form" in {name for name, _ in ancestors}:
            found[-1]["fields"].append(attrs.get("name"))
    return found
