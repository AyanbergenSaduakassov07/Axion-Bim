import assert from "node:assert/strict";
import { test } from "node:test";
import { blocks, inline } from "./markdown.ts";

test("paragraphs, bullet and numbered lists", () => {
  assert.deepEqual(blocks("Lead line\nsame para\n\n- a\n* b\n\n1. one\n2) two"), [
    { kind: "p", lines: ["Lead line", "same para"] },
    { kind: "ul", lines: ["a", "b"] },
    { kind: "ol", lines: ["one", "two"] },
  ]);
});

test("headings become bold paragraphs", () => {
  assert.deepEqual(blocks("## Summary\ntext"), [{ kind: "h", lines: ["Summary"] }, { kind: "p", lines: ["text"] }]);
});

test("bold and inline code", () => {
  assert.deepEqual(inline("a **b** `c` d"), [
    { kind: "text", text: "a " },
    { kind: "b", text: "b" },
    { kind: "text", text: " " },
    { kind: "code", text: "c" },
    { kind: "text", text: " d" },
  ]);
});
