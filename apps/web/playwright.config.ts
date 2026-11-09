import { defineConfig } from "@playwright/test";

const API_PORT = 8766;
const WEB_PORT = 5174;

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}`, trace: "retain-on-failure", colorScheme: "dark" },
  webServer: [
    {
      // fresh data dir + generated fixtures on every run; IFC fixtures are never committed outside tests/
      command: `rm -rf apps/web/.e2e && uv run python scripts/e2e_fixtures.py apps/web/.e2e && AXIOM_DATA_DIR=apps/web/.e2e/data uv run axiom serve --port ${API_PORT}`,
      cwd: "../..",
      env: { ANTHROPIC_API_KEY: "", OPENROUTER_API_KEY: "" },
      url: `http://127.0.0.1:${API_PORT}/api/v1/projects`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      env: { AXIOM_API: `http://127.0.0.1:${API_PORT}` },
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
    },
  ],
});
