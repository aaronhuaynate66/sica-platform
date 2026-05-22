import { fileURLToPath } from "url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    // happy-dom para tests de componentes React; los tests puros de lib/
    // funcionan igual en happy-dom.
    environment: "happy-dom",
    globals: false,
    include: [
      "lib/**/*.test.ts",
      "lib/**/__tests__/**/*.test.ts",
      "lib/**/__tests__/**/*.test.tsx",
      "components/**/__tests__/**/*.test.tsx",
    ],
    css: false,
    setupFiles: ["./vitest.setup.ts"],
  },
  // Disable PostCSS auto-discovery — el postcss.config.mjs es para Next.js
  // (string plugin spec) y rompe el loader de Vite. Tests no tocan CSS.
  css: {
    postcss: { plugins: [] },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
});
