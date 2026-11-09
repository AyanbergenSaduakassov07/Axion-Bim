import { cpSync, mkdirSync } from "node:fs";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const api = process.env.AXIOM_API ?? "http://127.0.0.1:8000";

/** Serve web-ifc wasm and the fragments worker from our own origin (D-08), copied from the pinned packages. */
function viewerAssets(): Plugin {
  return {
    name: "axiom-viewer-assets",
    config() { // before the dev server indexes public/
      mkdirSync("public/wasm", { recursive: true });
      for (const f of ["web-ifc.wasm", "web-ifc-mt.wasm"]) cpSync(`node_modules/web-ifc/${f}`, `public/wasm/${f}`);
      cpSync("node_modules/@thatopen/fragments/dist/Worker/worker.mjs", "public/fragments-worker.mjs");
    },
  };
}

export default defineConfig({
  plugins: [viewerAssets(), react(), tailwindcss()],
  server: { proxy: { "/api": api } }, // API has no CORS: same-origin via the dev proxy
  worker: { format: "es" },
});
