import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";

import react from "@vitejs/plugin-react";
import proxyOptions from "./proxyOptions.js";

// import.meta.dirname needs Node 20.11+; Frappe Cloud v15 benches build with Node 18.
const here = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8080,
    host: "0.0.0.0",
    proxy: proxyOptions,
  },
  resolve: {
    alias: {
      "@": path.resolve(here, "src"),
    },
  },
  build: {
    outDir: "../ia_maturity/public/grc",
    emptyOutDir: true,
    target: "es2015",
  },
});
