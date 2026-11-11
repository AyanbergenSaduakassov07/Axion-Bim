import { CalendarClock, UserRound } from "lucide-react";
import { useState } from "react";
import type { Finding, Issue, IssueUpdate } from "../api/client";
import { authorName, setAuthorName, useIssueHistory, useUpdateIssues } from "../api/queries";
import { tokenLabel, useT } from "../i18n";
import { btn, btnPrimary, date, fmtDate, input } from "../ui";
import { ISSUE_STATES, isOverdue, stateOf, todayIso } from "./issues";

const STATE_CLS: Record<string, string> = {
  open: "border-line text-fg",
  in_progress: "border-accent text-accent",
  disputed: "border-sev-high text-sev-high",
  accepted: "border-line text-muted",
  closed: "border-line text-muted line-through",
};

/** Compact issue cell: state, assignee, due date (red when overdue). */
export function IssueCell({ issue }: { issue: Issue | undefined }) {
  const { t } = useT();
  const state = stateOf(issue);
  const late = isOverdue(issue, todayIso());
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 text-xs">
      <span className={`shrink-0 rounded border px-1 ${STATE_CLS[state]}`}>{tokenLabel(t, state)}</span>
      {issue?.assignee && <span className="truncate text-muted">{issue.assignee}</span>}
      {issue?.due_date && (
        <span className={late ? "font-medium text-sev-critical" : "text-muted"} title={late ? t("Overdue") : undefined}>
          {fmtDate(`${issue.due_date}T00:00`)}
        </span>
      )}
    </span>
  );
}

/** Applies state / assignee / due date to every finding currently shown by the filters (e.g. one rule). */
export function BulkIssueBar({ modelId, rows }: { modelId: number; rows: Finding[] }) {
  const { t } = useT();
  const save = useUpdateIssues(modelId);
  const [state, setState] = useState("");
  const [assignee, setAssignee] = useState("");
  const [due, setDue] = useState("");
  const changes: Partial<IssueUpdate> = {
    ...(state && { state: state as IssueUpdate["state"] }),
    ...(assignee.trim() && { assignee: assignee.trim() }),
    ...(due && { due_date: due }),
  };
  const ready = rows.length > 0 && Object.keys(changes).length > 0;
  const submit = () => {
    if (!ready) return;
    save.mutate({ identity_keys: rows.map((r) => r.identity_key), ...changes }, { onSuccess: () => (setState(""), setAssignee(""), setDue("")) });
  };
  return (
    <form onSubmit={(e) => (e.preventDefault(), submit())} className="flex flex-wrap items-end gap-1.5 rounded border border-dashed border-line px-1.5 pb-1 pt-0.5" aria-label={t("Bulk issue update")}>
      <label className="text-xs text-muted">
        <span className="block">{t("Set state")}</span>
        <select className={`${input} text-fg`} value={state} onChange={(e) => setState(e.target.value)}>
          <option value="">—</option>
          {ISSUE_STATES.map((s) => (
            <option key={s} value={s}>{tokenLabel(t, s)}</option>
          ))}
        </select>
      </label>
      <label className="text-xs text-muted">
        <span className="block">{t("Assignee")}</span>
        <input className={`${input} w-32 text-fg`} maxLength={120} value={assignee} onChange={(e) => setAssignee(e.target.value)} />
      </label>
      <label className="text-xs text-muted">
        <span className="block">{t("Due date")}</span>
        <input type="date" className={`${input} text-fg`} value={due} onChange={(e) => setDue(e.target.value)} />
      </label>
      <button type="submit" className={btnPrimary} disabled={!ready || save.isPending}>
        {t("Apply to {n}", { n: rows.length })}
      </button>
      {save.isError && <span role="alert" className="pb-1.5 text-xs text-sev-critical">{t("Could not save")}</span>}
    </form>
  );
}

/** Single-finding triage in the detail panel. */
export function IssueEditor({ modelId, identityKey, issue }: { modelId: number; identityKey: string; issue: Issue | undefined }) {
  const { t } = useT();
  const save = useUpdateIssues(modelId);
  const [note, setNote] = useState(issue?.note ?? "");
  const put = (fields: Partial<IssueUpdate>) => save.mutate({ identity_keys: [identityKey], ...fields });
  return (
    <div className="space-y-2 rounded border border-line p-2" aria-label={t("Issue")}>
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs text-muted">
          <span className="block">{t("State")}</span>
          <select className={`${input} text-fg`} value={stateOf(issue)} onChange={(e) => put({ state: e.target.value as IssueUpdate["state"] })}>
            {ISSUE_STATES.map((s) => (
              <option key={s} value={s}>{tokenLabel(t, s)}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          <span className="flex items-center gap-1"><UserRound size={12} aria-hidden />{t("Assignee")}</span>
          <input
            key={`a-${issue?.assignee}`}
            className={`${input} w-36 text-fg`}
            maxLength={120}
            defaultValue={issue?.assignee ?? ""}
            onBlur={(e) => e.target.value.trim() !== (issue?.assignee ?? "") && put({ assignee: e.target.value.trim() || null })}
          />
        </label>
        <label className="text-xs text-muted">
          <span className="flex items-center gap-1"><CalendarClock size={12} aria-hidden />{t("Due date")}</span>
          <input type="date" className={`${input} text-fg`} value={issue?.due_date ?? ""} onChange={(e) => put({ due_date: e.target.value || null })} />
        </label>
      </div>
      <label className="block text-xs text-muted">
        <span className="block">{t("Note")}</span>
        <textarea className={`${input} h-16 w-full py-1 text-fg`} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="flex items-center gap-2">
        <button className={btn} disabled={note === (issue?.note ?? "") || save.isPending} onClick={() => put({ note: note || null })}>
          {t("Save note")}
        </button>
        {save.isError && <span role="alert" className="text-xs text-sev-critical">{t("Could not save")}</span>}
        {isOverdue(issue, todayIso()) && <span className="text-xs font-medium text-sev-critical">{t("Overdue")}</span>}
        <label className="ml-auto flex items-center gap-1 text-xs text-muted">
          {t("Your name")}
          <input className={`${input} w-32 text-fg`} maxLength={120} defaultValue={authorName()} onBlur={(e) => setAuthorName(e.target.value.trim())} />
        </label>
      </div>
      <IssueHistory modelId={modelId} identityKey={identityKey} />
    </div>
  );
}

/** Who changed what and when (D-41). Loaded only when opened. */
function IssueHistory({ modelId, identityKey }: { modelId: number; identityKey: string }) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const h = useIssueHistory(modelId, identityKey, open).data;
  const shown = (field: string, v: string | null) => (v == null || v === "" ? "—" : field === "state" ? tokenLabel(t, v) : v);
  return (
    <details className="text-xs" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className="cursor-pointer text-muted">{t("History")}</summary>
      {h && h.length === 0 && <p className="py-1 text-muted">{t("No changes yet.")}</p>}
      <ol className="space-y-0.5 py-1">
        {h?.map((e, i) => (
          <li key={i} className="flex gap-2">
            <span className="shrink-0 text-muted">{date(e.at)}</span>
            <span>
              {t(e.field === "state" ? "State" : e.field === "assignee" ? "Assignee" : e.field === "due_date" ? "Due date" : "Note")}: {shown(e.field, e.old)} → {shown(e.field, e.new)}
              {e.author && <span className="text-muted"> · {e.author}</span>}
            </span>
          </li>
        ))}
      </ol>
    </details>
  );
}
