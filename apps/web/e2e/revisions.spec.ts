import { expect, test, type APIRequestContext } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "../../..");
const IFC = (name: string) => path.join(ROOT, `apps/web/.e2e/${name}.ifc`);
const IDS = path.join(ROOT, "examples/ids/structural-basic.ids");
const SHOTS = process.env.AXIOM_SHOTS;
const API = "/api/v1";

async function json<T>(r: ReturnType<APIRequestContext["get"]>): Promise<T> {
  const res = await r;
  expect(res.ok(), `${res.url()} → ${res.status()}`).toBeTruthy();
  return (await res.json()) as T;
}

/** Upload one revision through the API and wait for its pipeline (ingest → audit → compare) to finish. */
async function upload(request: APIRequestContext, modelId: number, name: string, idsHash: string): Promise<void> {
  const file = { name: `${name}.ifc`, mimeType: "application/octet-stream", buffer: readFileSync(IFC(name)) };
  const { job_id } = await json<{ job_id: number }>(
    request.post(`${API}/models/${modelId}/revisions`, { multipart: { file, ids_hash: idsHash } }),
  );
  await expect
    .poll(async () => (await json<{ status: string }>(request.get(`${API}/jobs/${job_id}`))).status, { timeout: 60_000 })
    .toBe("done");
}

test("r2 → r3: recurring MAT-001 on C2 is listed and focuses C2 in the viewer", async ({ page, request }) => {
  test.setTimeout(180_000); // three pipeline jobs + viewer load
  const project = await json<{ id: number }>(request.post(`${API}/projects`, { data: { name: "Revision Tower" } }));
  const model = await json<{ id: number }>(request.post(`${API}/projects/${project.id}/models`, { data: { name: "Structure" } }));
  const ids = { name: "structural-basic.ids", mimeType: "application/xml", buffer: readFileSync(IDS) };
  const { ids_hash } = await json<{ ids_hash: string }>(request.post(`${API}/ids`, { multipart: { file: ids } }));
  for (const name of ["rev1", "rev2", "rev3"]) await upload(request, model.id, name, ids_hash);

  const revs = await json<{ id: number }[]>(request.get(`${API}/models/${model.id}/revisions`));
  const [r2, r3] = revs.slice(-2).map((r) => r.id);
  const [cmp] = await json<{ id: number; base_revision_id: number }[]>(request.get(`${API}/revisions/${r3}/comparisons`));
  const events = await json<{ event: string; rule_id: string; element_name: string; global_id: string }[]>(
    request.get(`${API}/comparisons/${cmp.id}/events`),
  );
  // revisions.yaml rev2_rev3: MAT-001 {C2: recurring}
  const c2 = events.find((e) => e.event === "recurring" && e.rule_id === "MAT-001" && e.element_name === "C2")!;
  expect(c2).toBeTruthy();

  await page.goto(`/models/${model.id}/revisions?base=${r2}&head=${r3}`);
  const recurring = page.getByRole("region", { name: "recurring findings" });
  await expect(recurring).toBeVisible();
  await page.waitForFunction(() => (window as any).__axiomViewer, null, { timeout: 60_000 });
  await recurring.getByRole("button", { name: /recurring MAT-001 C2/ }).click();
  await expect
    .poll(() => page.evaluate(() => (window as any).__axiomViewer.lastFocused()), { timeout: 60_000 })
    .toBe(c2.global_id);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/revisions.png`, fullPage: true });

  await page.goto(`/revisions/${r3}/quantities`);
  await expect(page.getByRole("columnheader", { name: "Δ vs r2" })).toBeVisible();
});
