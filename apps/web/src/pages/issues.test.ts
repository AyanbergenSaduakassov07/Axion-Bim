import assert from "node:assert/strict";
import { test } from "node:test";
import type { Issue } from "../api/client";
import { isOverdue, stateOf } from "./issues.ts";

const issue = (state: Issue["state"], due_date: string | null): Issue =>
  ({ identity_key: "a".repeat(40), state, due_date, assignee: null, note: null, updated_at: "" }) as Issue;

test("untriaged findings are open", () => assert.equal(stateOf(undefined), "open"));

test("overdue only when the due date passed and work is not finished", () => {
  assert.equal(isOverdue(issue("open", "2026-01-01"), "2026-01-02"), true);
  assert.equal(isOverdue(issue("in_progress", "2026-01-02"), "2026-01-02"), false);
  assert.equal(isOverdue(issue("closed", "2026-01-01"), "2026-01-02"), false);
  assert.equal(isOverdue(issue("accepted", "2026-01-01"), "2026-01-02"), false);
  assert.equal(isOverdue(issue("open", null), "2026-01-02"), false);
  assert.equal(isOverdue(undefined, "2026-01-02"), false);
});
