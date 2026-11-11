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
  await page.waitForURL(/\/projects\/\d+$/); // creating a project opens it
  const projectUrl = page.url();

  await page.getByLabel("Model name").fill("Structure");
  await page.getByRole("button", { name: "Create model" }).click();
  await page.getByRole("link", { name: "Upload revision" }).click();

  await page.getByLabel("IFC file").setInputFiles(REV1);
  await page.getByLabel("IDS requirements (optional)").selectOption("new"); // new file joins the project library
  await page.getByLabel("IDS file").setInputFiles(IDS);
  await page.getByRole("button", { name: "Upload and audit" }).click();
  await page.getByRole("link", { name: "Open Quality Center" }).click({ timeout: 45_000 });

  // rev1 golden: MAT-001 on C2, C3 + IDS STR-COL material facet on C2, C3
  await expect(page.getByTestId("finding-count")).toHaveText("4 of 4 findings");
  await expect(page.getByTestId("mhi-score")).toHaveText("95.2");
  await expect(page.getByTestId("gate-decision")).toHaveText("Accepted with comments"); // open high findings, none critical
  await expect(page.getByText("Requirements checked: structural-basic")).toBeVisible(); // library name, not a hash

  const grid = page.getByRole("grid", { name: "Findings" });
  await grid.locator("[tabindex='0']").focus();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("region", { name: "Finding detail" })).toBeVisible();
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/quality.png`, fullPage: true });

  await page.getByLabel("GlobalId or name").fill("C3");
  await expect(page.getByTestId("finding-count")).toHaveText("2 of 4 findings");

  // finding row → viewer focuses the same GlobalId (dev-only hook)
  await page.waitForFunction(() => (window as any).__axiomViewer, null, { timeout: 60_000 });
  const row = grid.getByRole("row").nth(1);
  await row.click();
  const gid = (await row.getByRole("gridcell").nth(5).textContent())!.trim();
  await expect.poll(() => page.evaluate(() => (window as any).__axiomViewer.lastFocused())).toBe(gid);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/quality-3d.png`, fullPage: true });

  // navigation buttons + keys move the camera (trackpad users have no easy orbit/pan)
  const distance = () => page.evaluate(() => (window as any).__axiomViewer.distance() as number);
  const before = await distance();
  await page.getByRole("button", { name: "Zoom in" }).click();
  await expect.poll(distance).toBeLessThan(before * 0.9);
  await page.getByRole("button", { name: "Fit model" }).click();
  await expect.poll(distance).toBeGreaterThan(before * 0.99); // fit transition done
  await page.getByRole("application").press("-");
  await expect.poll(distance).toBeGreaterThan(before * 1.1);

  // Explorer: tree pick shows the element panel with its findings
  await page.getByRole("link", { name: "3D model" }).click();
  await page.getByRole("button", { name: /^C3 IfcColumn/ }).click();
  await expect(page.getByText(gid)).toBeVisible();
  await expect(page.getByText("Findings (2)")).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => (window as any).__axiomViewer?.lastFocused()), { timeout: 60_000 })
    .toBe(gid); // a pick made while the viewer loads is applied once it is ready
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/explorer.png`, fullPage: true });

  if (SHOTS) {
    await page.goto(projectUrl);
    await expect(page.getByText("Elements by class")).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/overview.png`, fullPage: true });
  }
});
