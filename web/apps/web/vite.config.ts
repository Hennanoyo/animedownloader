import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  optimizeDeps: {
    exclude: ["jassub"],
    // JASSUB is kept as source so its worker/WASM assets can be resolved by Vite.
    // Its nested throughput dependency is CommonJS and must be pre-bundled into ESM.
    include: ["jassub > throughput"],
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  test: {
    globals: true,
  },
});
