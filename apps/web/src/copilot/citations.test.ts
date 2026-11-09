import assert from "node:assert/strict";
import { test } from "node:test";
import { splitCitations } from "./citations.ts";

test("splits answer text into text and citation parts", () => {
  assert.deepEqual(splitCitations("C2 [[el:2O2Fr$t4X7Zf8NOew3FLOH]] lacks material ([[finding:ab12]])."), [
    { kind: "text", text: "C2 " },
    { kind: "cite", type: "element", id: "2O2Fr$t4X7Zf8NOew3FLOH" },
    { kind: "text", text: " lacks material (" },
    { kind: "cite", type: "finding", id: "ab12" },
    { kind: "text", text: ")." },
  ]);
});

test("plain text stays one part", () => {
  assert.deepEqual(splitCitations("not available"), [{ kind: "text", text: "not available" }]);
});
