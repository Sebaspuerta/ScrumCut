// @vitest-environment node
import { expect, it } from "vitest";

import { generateTypes } from "../../scripts/generate-types.mjs";
import committed from "./schema.d.ts?raw";

const normalize = (text: string) => text.replace(/\r\n/g, "\n").trimEnd();

it("los tipos de la API están generados desde el openapi.json actual (npm run gen:types)", async () => {
  expect(normalize(committed)).toBe(normalize(await generateTypes()));
});
