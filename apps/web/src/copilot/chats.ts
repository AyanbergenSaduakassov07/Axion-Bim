import type { CopilotAnswer } from "../api/client";

// Conversations live in this browser only (per project): the backend keeps no chat state (D-31).
export type Msg = { role: "user"; text: string } | { role: "assistant"; answer: CopilotAnswer } | { role: "error"; text: string };
export type Chat = { id: string; title: string; updated: number; messages: Msg[] };

const MAX_CHATS = 50;
const HISTORY_TURNS = 10; // backend accepts at most 10 earlier exchanges
const key = (projectId: number) => `axiom.chats.${projectId}`;

export function loadChats(projectId: number): Chat[] {
  try {
    const raw = localStorage.getItem(key(projectId));
    return raw ? (JSON.parse(raw) as Chat[]) : [];
  } catch {
    return []; // private window or corrupted entry: start empty
  }
}

export function saveChats(projectId: number, chats: Chat[]) {
  try {
    localStorage.setItem(key(projectId), JSON.stringify(chats.slice(0, MAX_CHATS)));
  } catch {
    // storage full or blocked: the chat still works for this session
  }
}

/** Earlier (question, answer) pairs to send with the next question; errors and unanswered questions are skipped. */
export function historyOf(messages: Msg[]): { question: string; answer: string }[] {
  const pairs: { question: string; answer: string }[] = [];
  messages.forEach((m, i) => {
    const next = messages[i + 1];
    if (m.role === "user" && next?.role === "assistant") pairs.push({ question: m.text, answer: next.answer.answer });
  });
  return pairs.slice(-HISTORY_TURNS);
}

/** Array.findLastIndex without raising the TS lib target. */
export function lastIndex<T>(xs: T[], pred: (x: T) => boolean): number {
  for (let i = xs.length - 1; i >= 0; i--) if (pred(xs[i])) return i;
  return -1;
}
