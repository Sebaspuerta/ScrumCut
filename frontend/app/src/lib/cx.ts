/** Une clases de CSS por módulo; las que no existen o no aplican (undefined, false, "") se omiten. */
export function cx(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(" ");
}
