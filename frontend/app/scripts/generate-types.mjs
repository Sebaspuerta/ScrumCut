// Genera src/api/schema.d.ts desde openapi.json (drf-spectacular). Los tipos de la API nunca se escriben a mano.
// Uso: npm run gen:types. La prueba src/api/schema.test.ts falla si el archivo quedó desactualizado.
import { writeFile } from "node:fs/promises";
import process from "node:process";
import { pathToFileURL, URL } from "node:url";
import openapiTS, { astToString, COMMENT_HEADER } from "openapi-typescript";

const SCHEMA = new URL("../openapi.json", import.meta.url);
const TYPES = new URL("../src/api/schema.d.ts", import.meta.url);

export async function generateTypes() {
  return COMMENT_HEADER + astToString(await openapiTS(SCHEMA));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  await writeFile(TYPES, await generateTypes());
}
