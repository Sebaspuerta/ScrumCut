// Estándar del frontend (AGENTS.md): TypeScript estricto, hooks de React, componentes cortos y
// nada en el almacenamiento del navegador ni estilos en línea.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";

const MAX_COMPONENT_FILE_LINES = 150;
const MAX_FUNCTION_LINES = 30;
const NO_BROWSER_STORAGE = "La sesión vive en la cookie del servidor: nada se guarda en el navegador.";

export default defineConfig(
  { ignores: ["src/api/schema.d.ts"] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } },
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "localStorage", message: NO_BROWSER_STORAGE },
        { name: "sessionStorage", message: NO_BROWSER_STORAGE },
      ],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "localStorage", message: NO_BROWSER_STORAGE },
        { object: "window", property: "sessionStorage", message: NO_BROWSER_STORAGE },
        { object: "document", property: "cookie", message: NO_BROWSER_STORAGE },
      ],
      "no-restricted-syntax": [
        "error",
        { selector: "JSXAttribute[name.name='style']", message: "Sin estilos en línea: CSS por módulo con tokens." },
        { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: "Sin HTML sin escapar." },
      ],
      "no-console": "error",
      "max-lines": ["error", { max: MAX_COMPONENT_FILE_LINES, skipBlankLines: true, skipComments: true }],
    },
  },
  {
    files: ["**/*.ts"],
    ignores: ["**/*.test.ts"],
    rules: {
      "max-lines-per-function": ["error", { max: MAX_FUNCTION_LINES, skipBlankLines: true, skipComments: true }],
    },
  },
  { files: ["**/*.js", "**/*.mjs"], extends: [tseslint.configs.disableTypeChecked] },
);
