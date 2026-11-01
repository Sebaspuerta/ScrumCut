/** Un ref que fija una variable de CSS por el CSSOM: un valor que depende de los datos (el ancho de una barra)
 * nunca va en el atributo style, que la CSP estricta no permite. */
export function cssVar(name: string, value: string): (node: HTMLElement | null) => void {
  return (node) => {
    node?.style.setProperty(name, value);
  };
}
