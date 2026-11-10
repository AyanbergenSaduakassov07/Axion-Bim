import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { ru } from "./i18n-ru.ts";

const SRC = new URL(".", import.meta.url).pathname;

// keys reached through variables (tables, tokens from the backend) rather than a t("...") literal
const INDIRECT = [
  ...["critical", "high", "medium", "low", "info"],
  ...["pass", "fail", "warning", "error", "not evaluated", "not applicable"],
  ...["new", "resolved", "persistent", "recurring", "changed", "uncertain"],
  ...["property completeness", "ids compliance", "geometry integrity", "spatial integrity"],
  ...["material completeness", "classification quality", "model consistency"],
  ...["element removed", "rule version changed"],
  ...["added", "removed", "modified", "new finding", "recurring finding"],
  ...["class", "storey", "material", "classification", "qto", "geometry"],
  ...["metadata", "identity", "spatial", "quantity"],
  ...["open", "in progress", "disputed", "accepted", "closed", "overdue", "Issue"],
  ...["Severity", "Status", "Category", "Rule", "Class", "Element", "GlobalId", "Message"],
  ...["Change", "Path", "Old", "New"],
  ...["Zoom in", "Zoom out", "Fit model", "Tilt up", "Rotate left", "Rotate right", "Tilt down"],
  ...["Pan up", "Pan left", "Pan right", "Pan down", "Orbit", "Pan"],
  "What changed between the last two revisions?",
  "Why did the health index change?",
  "Which elements are missing a material?",
  "What is the beam volume in the latest revision, and how was it computed?",
];

function tsxFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((d) =>
    d.isDirectory() ? tsxFiles(join(dir, d.name)) : d.name.endsWith(".tsx") ? [join(dir, d.name)] : [],
  );
}

test("every UI string has a Russian translation", () => {
  const literal = /\bt\(\s*"((?:[^"\\]|\\.)*)"/g;
  const keys = new Set(INDIRECT);
  for (const f of tsxFiles(SRC)) for (const m of readFileSync(f, "utf8").matchAll(literal)) keys.add(m[1]);
  const missing = [...keys].filter((k) => !(k in ru));
  assert.deepEqual(missing, [], `add these to i18n-ru.ts:\n${missing.join("\n")}`);
});

test("translations keep every {placeholder}", () => {
  const vars = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join();
  const broken = Object.entries(ru).filter(([en, r]) => vars(en) !== vars(r)).map(([en]) => en);
  assert.deepEqual(broken, []);
});
