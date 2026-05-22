import { fileURLToPath } from "url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    globals: false,
    include: ["lib/**/*.test.ts", "lib/**/__tests__/**/*.test.ts"],
    css: false,
  },
  // Disable PostCSS auto-discovery — the project's postcss.config.mjs is
  // shaped for Next.js (string plugin spec) and breaks Vite's loader.
  // Tests don't touch CSS, so this is a no-op for them.
  css: {
    postcss: { plugins: [] },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
});
