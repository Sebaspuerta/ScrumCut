import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Django sirve la compilación como estáticos: la base debe coincidir con STATIC_URL + "app/".
const BUILD_BASE = "/static/app/";
// En desarrollo, el servidor de Vite atiende /app/ y pasa todo lo demás (API, cuenta, estáticos y
// las pantallas en plantillas) a Django. Se conserva el Host para que la comprobación CSRF de Django
// vea el mismo origen que el navegador.
const DEV_BASE = "/app/";
const DJANGO = "http://127.0.0.1:8000";
const NOT_THE_APP = "^/(?!app(?:/|$))";

export default defineConfig(({ command }) => ({
  base: command === "build" ? BUILD_BASE : DEV_BASE,
  plugins: [react()],
  build: {
    outDir: "../static/app",
    emptyOutDir: true,
    manifest: "manifest.json",
    rolldownOptions: { input: "src/main.tsx" },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { [NOT_THE_APP]: { target: DJANGO, changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["src/test/setup.ts"],
  },
}));
