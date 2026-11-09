import { expect, test } from "@playwright/test";

// The e2e server has no ANTHROPIC_API_KEY: the real copilot must stay hidden. The "available" case stubs the
// two copilot endpoints so citation rendering is checked without a billed model call.
test("copilot is hidden without an API key, everything else renders", async ({ page, request }) => {
  const p = await (await request.post("/api/v1/projects", { data: { name: "No Key Tower" } })).json();
  await page.goto(`/projects/${p.id}`);
  await expect(page.getByRole("heading", { name: "Models" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Copilot" })).toHaveCount(0);
});

test("copilot answer renders citation chips that deep-link to viewer and finding", async ({ page, request }) => {
  const p = await (await request.post("/api/v1/projects", { data: { name: "Stub Tower" } })).json();
  await page.route("**/api/v1/copilot", (r) => r.fulfill({ json: { available: true, model: "stub" } }));
  await page.route("**/api/v1/copilot/query", (r) =>
    r.fulfill({
      json: {
        answer: "C2 [[el:2O2Fr$t4X7Zf8NOew3FLOH]] has no material ([[finding:ab12]]).",
        citations: [
          { type: "element", id: "2O2Fr$t4X7Zf8NOew3FLOH", label: "C2", revision_id: 7 },
          { type: "finding", id: "ab12", label: "MAT-001 C2", revision_id: 7 },
        ],
        tool_calls: [{ name: "findings", input: { revision_id: 7 } }],
        unverified: ["0000000000000000000000"],
        stop_reason: "end_turn",
      },
    }),
  );
  await page.goto(`/projects/${p.id}`);
  await page.getByLabel("Ask about this project").fill("Which elements lack material?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByRole("link", { name: "C2", exact: true })).toHaveAttribute(
    "href",
    "/revisions/7/explorer?focus=2O2Fr%24t4X7Zf8NOew3FLOH",
  );
  await expect(page.getByRole("link", { name: "MAT-001 C2" })).toHaveAttribute("href", "/revisions/7/quality?finding=ab12");
  await expect(page.getByRole("alert")).toContainText("1 citation(s) could not be verified");
  await expect(page.getByText("1 tool call(s)")).toBeVisible();
});
