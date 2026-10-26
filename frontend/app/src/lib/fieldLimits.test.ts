import { describe, expect, it } from "vitest";

import schema from "../../openapi.json";
import { MAX_LENGTH } from "./fieldLimits";

interface SchemaField {
  maxLength?: number;
}

const components = schema.components.schemas as Record<string, { properties?: Record<string, SchemaField> }>;
const limits = Object.entries(MAX_LENGTH).flatMap(([name, fields]) =>
  Object.entries(fields).map(([field, max]) => ({ name, field, max: max })),
);
// El código de los formularios, para encontrar cada maxLength que se escribe.
const sources = import.meta.glob<string>(["../**/*.tsx", "!../**/*.test.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
});

describe("largo máximo de los campos", () => {
  it.each(limits)("$name, campo $field: coincide con openapi.json", ({ name, field, max }) => {
    const property = components[name]?.properties?.[field];

    expect(property, `${name}.${field} no existe en el esquema`).toBeDefined();
    expect(property?.maxLength, `${name}.${field} no trae maxLength en el esquema`).toBeDefined();
    expect(max).toBe(property?.maxLength);
  });

  it("todo maxLength de un formulario sale de MAX_LENGTH", () => {
    const loose = Object.entries(sources).flatMap(([file, code]) =>
      [...code.matchAll(/maxLength=\{([^}]*)\}/g)]
        .filter((match) => !match[1]?.startsWith("MAX_LENGTH."))
        .map((match) => `${file}: ${match[0]}`),
    );

    expect(loose).toEqual([]);
  });
});
