import assert from "node:assert/strict";
import { test } from "node:test";
import { historyOf, type Msg } from "./chats.ts";

const answer = (text: string) => ({ answer: text, citations: [], tool_calls: [], unverified: [], stop_reason: "end_turn" });

test("history pairs answered questions and skips errors", () => {
  const msgs: Msg[] = [
    { role: "user", text: "q1" },
    { role: "assistant", answer: answer("a1") },
    { role: "user", text: "q2" },
    { role: "error", text: "busy" },
    { role: "user", text: "q3" },
    { role: "assistant", answer: answer("a3") },
  ];
  assert.deepEqual(historyOf(msgs), [
    { question: "q1", answer: "a1" },
    { question: "q3", answer: "a3" },
  ]);
});
