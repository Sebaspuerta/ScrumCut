// Barras de las gráficas: el servidor manda su tamaño en atributos data- (porcentajes) y aquí se aplica
// con el CSSOM, porque la CSP no permite estilos en el HTML.
const SIZES = [
  ["data-bar-width", "barWidth", "width"],
  ["data-bar-height", "barHeight", "height"],
  ["data-bar-bottom", "barBottom", "bottom"],
];

for (const [attribute, key, property] of SIZES) {
  for (const bar of document.querySelectorAll(`[${attribute}]`)) {
    bar.style[property] = `${bar.dataset[key]}%`;
  }
}
