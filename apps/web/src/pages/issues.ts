import type { Issue } from "../api/client";

export const ISSUE_STATES = ["open", "in_progress", "disputed", "accepted", "closed"] as const;
export type IssueState = (typeof ISSUE_STATES)[number];
const DONE: ReadonlySet<string> = new Set(["accepted", "closed"]);

/** A finding nobody has triaged yet is an open issue. */
export const stateOf = (i: Issue | undefined): IssueState => i?.state ?? "open";

/** Due date passed and the issue is still being worked on. `today` is YYYY-MM-DD (local). */
export const isOverdue = (i: Issue | undefined, today: string) => !!i?.due_date && i.due_date < today && !DONE.has(i.state);

export const todayIso = () => new Date().toLocaleDateString("sv-SE"); // sv-SE formats as YYYY-MM-DD
