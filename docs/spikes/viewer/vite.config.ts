import { defineConfig } from "vite";
export default defineConfig({ build: { target: "esnext" }, esbuild: { target: "esnext" }, optimizeDeps: { esbuildOptions: { target: "esnext" } }, server: { port: 5199 } });
