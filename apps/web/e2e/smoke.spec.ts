import { expect, test } from "@playwright/test";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "../../..");
const REV1 = path.join(ROOT, "apps/web/.e2e/rev1.ifc");
const IDS = path.join(ROOT, "examples/ids/structural-basic.ids");
const SHOTS = process.env.AXIOM_SHOTS; // optional screenshot dir (scratchpad), never the repo

test("upload rev1, wait for the job, Quality Center shows the golden findings", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Project name").fill("Smoke Tower");
  await page.getByRole("button", { name: "Create project" }).click();
  await page.getByRole("link", { name: "Smoke Tower" }).click();

  await page.getByLabel("Model name").fill("Structure");
  await page.getByRole("button", { name: "Create model" }).click();
  await page.getByRole("link", { name: "Upload revision" }).click();

  await page.getByLabel("IFC file").setInputFiles(REV1);
  await page.getByLabel("IDS file").setInputFiles(IDS);
  await page.getByRole("button", { name: "Upload and audit" }).click();
  await page.getByRole("link", { name: "Open Quality Center" }).click({ timeout: 45_000 });

  // rev1 golden: MAT-001 on C2, C3 + IDS STR-COL material facet on C2, C3
  await expect(page.getByTestId("finding-count")).toHaveText("4 of 4 findings");
  await expect(page.getByTestId("mhi-score")).toHaveText("95.2");

  const grid = page.getByRole("grid", { name: "Findings" });
  await grid.locator("[tabindex='0']").focus();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("region", { name: "Finding detail" })).toBeVisible();
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/quality.png`, fullPage: true });

  await page.getByLabel("GlobalId or name").fill("C3");
  await expect(page.getByTestId("finding-count")).toHaveText("2 of 4 findings");

  if (SHOTS) {
    await page.goto("/projects/1");
    await expect(page.getByText("Elements by class")).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/overview.png`, fullPage: true });
  }
});
