import { describe, expect, it } from "vitest";

import schema from "../../openapi.json";
import { MAX_LENGTH, MAX_VALUE } from "./fieldLimits";

interface SchemaField {
  maxLength?: number;
  maximum?: number;
}

const components = schema.components.schemas as Record<string, { properties?: Record<string, SchemaField> }>;
const flatten = (limits: Record<string, Record<string, number>>) =>
  Object.entries(limits).flatMap(([name, fields]) =>
    Object.entries(fields).map(([field, max]) => ({ name, field, max })),
  );
// El código de los formularios, para encontrar cada maxLength y cada max que se escribe.
const sources = import.meta.glob<string>(["../**/*.tsx", "!../**/*.test.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
});

function looseAttributes(attribute: string, source: string, folder = "../"): string[] {
  const pattern = new RegExp(`\\s${attribute}=\\{([^}]*)\\}`, "g");
  const files = Object.entries(sources).filter(([file]) => file.startsWith(folder));
  return files.flatMap(([file, code]) =>
    [...code.matchAll(pattern)]
      .filter(([, value = ""]) => !value.startsWith(`${source}.`) && !value.startsWith(`${source}[`))
      .map((match) => `${file}: ${match[0].trim()}`),
  );
}

describe("topes de los campos", () => {
  it.each(flatten(MAX_LENGTH))("largo de $name.$field: coincide con openapi.json", ({ name, field, max }) => {
    const property = components[name]?.properties?.[field];

    expect(property, `${name}.${field} no existe en el esquema`).toBeDefined();
    expect(property?.maxLength, `${name}.${field} no trae maxLength en el esquema`).toBeDefined();
    expect(max).toBe(property?.maxLength);
  });

  it.each(flatten(MAX_VALUE))("valor de $name.$field: coincide con openapi.json", ({ name, field, max }) => {
    const property = components[name]?.properties?.[field];

    expect(property?.maximum, `${name}.${field} no trae maximum en el esquema`).toBeDefined();
    expect(max).toBe(property?.maximum);
  });

  // Comandas recibe su tope de cantidad en los datos del catálogo (max_quantity); inventario, del esquema.
  it("todo maxLength de un formulario sale de MAX_LENGTH y todo max de inventario, de MAX_VALUE", () => {
    expect(looseAttributes("maxLength", "MAX_LENGTH")).toEqual([]);
    expect(looseAttributes("max", "MAX_VALUE", "../inventory/")).toEqual([]);
  });
});
