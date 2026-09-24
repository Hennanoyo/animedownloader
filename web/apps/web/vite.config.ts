import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const jassubWasmSourceMapPattern =
  /\n?\/\/# sourceMappingURL=.*(?:\r?\n)?$/;

const stripJassubWasmSourceMap = {
  name: "strip-jassub-wasm-sourcemap",
  enforce: "pre" as const,
  load(id: string) {
    if (!/[\\/]jassub[\\/]dist[\\/]wasm[\\/]jassub-worker\\.js(?:$|\?)/.test(id)) {
      return null;
    }

    const code = readFileSync(id, "utf-8");
    if (!jassubWasmSourceMapPattern.test(code)) {
      return null;
    }

    return {
      code: code.replace(jassubWasmSourceMapPattern, ""),
      map: null,
    };
  },
};

export default defineConfig({
  plugins: [react(), stripJassubWasmSourceMap],
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
