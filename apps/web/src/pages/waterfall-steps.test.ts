import assert from "node:assert/strict";
import { test } from "node:test";
import { buildSteps } from "./waterfall-steps.ts";

test("steps run base -> largest dimension moves -> residual -> head", () => {
  const { steps, unchanged } = buildSteps(95.2, 91.0, { material_completeness: -3.0, ids_compliance: -1.0, naming: 0.01 }, [2, 3]);
  assert.deepEqual(
    steps.map((s) => [s.label, Number(s.from.toFixed(2)), Number(s.to.toFixed(2)), s.kind]),
    [
      ["r2", 0, 95.2, "total"],
      ["material completeness", 95.2, 92.2, "down"],
      ["ids compliance", 92.2, 91.2, "down"],
      ["other (re-weighting)", 91.2, 91, "down"],
      ["r3", 0, 91, "total"],
    ],
  );
  assert.equal(unchanged, 1);
});
