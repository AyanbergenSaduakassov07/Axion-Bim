import { useVirtualizer } from "@tanstack/react-virtual";
import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { Finding, Issue } from "../api/client";
import { tokenLabel, useT } from "../i18n";
import { Empty, input, SEVERITIES, Severity, Status } from "../ui";
import { IssueCell } from "./IssueControls";
import { ISSUE_STATES, isOverdue, stateOf, todayIso } from "./issues";

const ROW_H = 32;
const FILTERS = ["severity", "status", "category", "rule_id", "ifc_class"] as const;
type FilterKey = (typeof FILTERS)[number];
const LABEL: Record<FilterKey, string> = {
  severity: "Severity",
  status: "Status",
  category: "Category",
  rule_id: "Rule",
  ifc_class: "Class",
};
const COLS = [
  ["severity", "Severity", "w-24"],
  ["status", "Status", "w-28"],
  ["rule_id", "Rule", "w-40"],
  ["ifc_class", "Class", "w-28"],
  ["element_name", "Element", "w-28"],
  ["global_id", "GlobalId", "w-52"],
  ["issue", "Issue", "w-60"],
  ["message", "Message", "flex-1"],
] as const;
type SortKey = (typeof COLS)[number][0];
const SEV_RANK = Object.fromEntries(SEVERITIES.map((s, i) => [s, i]));

type Issues = Map<string, Issue>;
const OVERDUE = "overdue";

function compare(a: Finding, b: Finding, key: SortKey, issues: Issues) {
  if (key === "severity") return SEV_RANK[a.severity] - SEV_RANK[b.severity];
  if (key === "issue") return issueRank(issues.get(a.identity_key)) - issueRank(issues.get(b.identity_key));
  return String(a[key] ?? "").localeCompare(String(b[key] ?? ""));
}

const issueRank = (i: Issue | undefined) => ISSUE_STATES.indexOf(stateOf(i));

function matchesIssue(i: Issue | undefined, state: string, assignee: string, today: string) {
  if (state === OVERDUE ? !isOverdue(i, today) : state && stateOf(i) !== state) return false;
  return !assignee || (i?.assignee ?? "") === assignee;
}

function useFiltered(findings: Finding[], issues: Issues) {
  const [issueState, setIssueState] = useState("");
  const [assignee, setAssignee] = useState("");
  const [filters, setFilters] = useState<Partial<Record<FilterKey, string>>>({});
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "severity", dir: 1 });
  const options = useMemo(
    () => Object.fromEntries(FILTERS.map((k) => [k, [...new Set(findings.map((f) => f[k] ?? ""))].filter(Boolean).sort()])),
    [findings],
  );
  const assignees = useMemo(() => [...new Set([...issues.values()].map((i) => i.assignee ?? ""))].filter(Boolean).sort(), [issues]);
  const rows = useMemo(() => {
    const s = search.trim().toLowerCase();
    const today = todayIso();
    return findings
      .filter((f) => FILTERS.every((k) => !filters[k] || f[k] === filters[k]))
      .filter((f) => matchesIssue(issues.get(f.identity_key), issueState, assignee, today))
      .filter((f) => !s || (f.global_id ?? "").toLowerCase().includes(s) || (f.element_name ?? "").toLowerCase().includes(s))
      .sort((a, b) => compare(a, b, sort.key, issues) * sort.dir);
  }, [findings, issues, filters, search, sort, issueState, assignee]);
  const issue = { issueState, setIssueState, assignee, setAssignee, assignees };
  return { rows, options, filters, setFilters, search, setSearch, sort, setSort, issue };
}

export function FindingsTable({
  findings,
  selected,
  onSelect,
  toolbar,
  issues,
}: {
  findings: Finding[];
  selected: string | null;
  onSelect: (key: string | null) => void;
  /** Extra controls that act on the currently filtered rows. */
  toolbar?: (rows: Finding[]) => ReactNode;
  /** Triage state by identity_key; omit to hide the issue column. */
  issues?: Issues;
}) {
  const none = useMemo<Issues>(() => new Map(), []);
  const ft = useFiltered(findings, issues ?? none);
  const cols = issues ? COLS : COLS.filter(([k]) => k !== "issue");
  const minW = issues ? "min-w-[1260px]" : "min-w-[1000px]"; // fixed columns + room for the message
  const { t } = useT();
  const byRule = useMemo(() => {
    const n = new Map<string, number>();
    for (const f of findings) n.set(f.rule_id, (n.get(f.rule_id) ?? 0) + 1);
    return [...n].sort((a, b) => b[1] - a[1]);
  }, [findings]);
  const scroller = useRef<HTMLDivElement>(null);
  const v = useVirtualizer({ count: ft.rows.length, getScrollElement: () => scroller.current, estimateSize: () => ROW_H, overscan: 10 });
  const active = Math.max(0, ft.rows.findIndex((f) => f.identity_key === selected));

  const move = (i: number) => {
    const idx = Math.min(Math.max(i, 0), ft.rows.length - 1);
    if (idx < 0) return;
    onSelect(ft.rows[idx].identity_key);
    v.scrollToIndex(idx);
  };
  const onKey = (e: KeyboardEvent) => {
    const keys: Record<string, () => void> = {
      ArrowDown: () => move(selected ? active + 1 : 0),
      ArrowUp: () => move(active - 1),
      Home: () => move(0),
      End: () => move(ft.rows.length - 1),
      Escape: () => onSelect(null),
    };
    if (keys[e.key]) {
      e.preventDefault();
      keys[e.key]();
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {byRule.length > 1 && (
        <div className="flex flex-wrap items-center gap-1.5 border-b border-line p-2 text-xs">
          <span className="text-muted">{t("Issues by rule:")}</span>
          {byRule.map(([rule, n]) => {
            const on = ft.filters.rule_id === rule;
            return (
              <button
                key={rule}
                aria-pressed={on}
                onClick={() => ft.setFilters({ ...ft.filters, rule_id: on ? undefined : rule })}
                className={`cursor-pointer rounded border px-1.5 py-0.5 ${on ? "border-accent bg-raised" : "border-line hover:border-accent"}`}
              >
                {rule} <span className="text-muted">{n}</span>
              </button>
            );
          })}
        </div>
      )}
      <div className="flex flex-wrap items-end gap-2 border-b border-line p-2">
        {FILTERS.map((k) => (
          <label key={k} className="text-xs text-muted">
            <span className="block">{t(LABEL[k])}</span>
            <select
              className={`${input} max-w-44 text-fg`}
              value={ft.filters[k] ?? ""}
              onChange={(e) => ft.setFilters({ ...ft.filters, [k]: e.target.value || undefined })}
            >
              <option value="">{t("All")}</option>
              {ft.options[k].map((o) => (
                <option key={o} value={o}>
                  {k === "rule_id" || k === "ifc_class" ? o : tokenLabel(t, o)}
                </option>
              ))}
            </select>
          </label>
        ))}
        {issues && (
          <>
            <label className="text-xs text-muted">
              <span className="block">{t("Issue state")}</span>
              <select className={`${input} text-fg`} value={ft.issue.issueState} onChange={(e) => ft.issue.setIssueState(e.target.value)}>
                <option value="">{t("All")}</option>
                {[...ISSUE_STATES, OVERDUE].map((s) => (
                  <option key={s} value={s}>{tokenLabel(t, s)}</option>
                ))}
              </select>
            </label>
            {ft.issue.assignees.length > 0 && (
              <label className="text-xs text-muted">
                <span className="block">{t("Assignee")}</span>
                <select className={`${input} max-w-36 text-fg`} value={ft.issue.assignee} onChange={(e) => ft.issue.setAssignee(e.target.value)}>
                  <option value="">{t("All")}</option>
                  {ft.issue.assignees.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}
        <label className="text-xs text-muted">
          <span className="block">{t("GlobalId or name")}</span>
          <input type="search" className={`${input} w-56 text-fg`} value={ft.search} onChange={(e) => ft.setSearch(e.target.value)} />
        </label>
        {toolbar?.(ft.rows)}
        <span className="ml-auto pb-1.5 text-xs text-muted" aria-live="polite" data-testid="finding-count">
          {t("{n} of {total} findings", { n: ft.rows.length, total: findings.length })}
        </span>
      </div>
      <div role="grid" aria-rowcount={ft.rows.length + 1} aria-label={t("Findings")} className="flex min-h-0 flex-1 flex-col overflow-x-auto text-sm">
        <div role="row" className={`flex border-b border-line bg-raised text-xs text-muted ${minW}`}>
          {cols.map(([key, label, w]) => {
            const on = ft.sort.key === key;
            return (
              <div key={key} role="columnheader" aria-sort={on ? (ft.sort.dir === 1 ? "ascending" : "descending") : "none"} className={`${w} shrink-0`}>
                <button
                  className="w-full cursor-pointer px-2 py-1.5 text-left font-medium hover:text-fg"
                  onClick={() => ft.setSort({ key, dir: on ? (-ft.sort.dir as 1 | -1) : 1 })}
                >
                  {t(label)} {on ? (ft.sort.dir === 1 ? "▲" : "▼") : ""}
                </button>
              </div>
            );
          })}
        </div>
        {ft.rows.length === 0 ? (
          <Empty>{findings.length === 0 ? t("No open issues: nothing failed, warned or errored in this audit.") : t("No findings match the filters.")}</Empty>
        ) : (
          <div
            ref={scroller}
            tabIndex={0}
            onKeyDown={onKey}
            aria-activedescendant={selected ? `f-${selected}` : undefined}
            className={`relative min-h-64 flex-1 overflow-y-auto overflow-x-hidden ${minW}`}
          >
            <div style={{ height: v.getTotalSize() }} className="relative">
              {v.getVirtualItems().map((it) => {
                const f = ft.rows[it.index];
                const on = f.identity_key === selected;
                return (
                  <div
                    key={f.identity_key}
                    id={`f-${f.identity_key}`}
                    role="row"
                    aria-rowindex={it.index + 2}
                    aria-selected={on}
                    onClick={() => onSelect(f.identity_key)}
                    style={{ height: ROW_H, transform: `translateY(${it.start}px)` }}
                    className={`absolute inset-x-0 top-0 flex cursor-pointer items-center border-b border-line ${on ? "bg-raised outline outline-1 -outline-offset-1 outline-accent" : "hover:bg-raised"}`}
                  >
                    <Cell w="w-24"><Severity value={f.severity} /></Cell>
                    <Cell w="w-28"><Status value={f.status} /></Cell>
                    <Cell w="w-40">{f.rule_id}</Cell>
                    <Cell w="w-28">{f.ifc_class ?? "—"}</Cell>
                    <Cell w="w-28" title={f.element_name ?? undefined}>{f.element_name ?? "—"}</Cell>
                    <Cell w="w-52" mono>{f.global_id ?? t("model")}</Cell>
                    {issues && <Cell w="w-60"><IssueCell issue={issues.get(f.identity_key)} /></Cell>}
                    <Cell w="flex-1" title={f.message}>{f.message}</Cell>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Cell({ w, mono, title, children }: { w: string; mono?: boolean; title?: string; children: ReactNode }) {
  return (
    <div role="gridcell" title={title} className={`${w} min-w-0 shrink-0 truncate px-2 ${mono ? "font-mono text-xs" : ""}`}>
      {children}
    </div>
  );
}
