import { useVirtualizer } from "@tanstack/react-virtual";
import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { Finding } from "../api/client";
import { Empty, input, SEVERITIES, Severity, Status } from "../ui";

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
  ["message", "Message", "flex-1"],
] as const;
type SortKey = (typeof COLS)[number][0];
const SEV_RANK = Object.fromEntries(SEVERITIES.map((s, i) => [s, i]));

function compare(a: Finding, b: Finding, key: SortKey) {
  if (key === "severity") return SEV_RANK[a.severity] - SEV_RANK[b.severity];
  return String(a[key] ?? "").localeCompare(String(b[key] ?? ""));
}

function useFiltered(findings: Finding[]) {
  const [filters, setFilters] = useState<Partial<Record<FilterKey, string>>>({});
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "severity", dir: 1 });
  const options = useMemo(
    () => Object.fromEntries(FILTERS.map((k) => [k, [...new Set(findings.map((f) => f[k] ?? ""))].filter(Boolean).sort()])),
    [findings],
  );
  const rows = useMemo(() => {
    const s = search.trim().toLowerCase();
    return findings
      .filter((f) => FILTERS.every((k) => !filters[k] || f[k] === filters[k]))
      .filter((f) => !s || (f.global_id ?? "").toLowerCase().includes(s) || (f.element_name ?? "").toLowerCase().includes(s))
      .sort((a, b) => compare(a, b, sort.key) * sort.dir);
  }, [findings, filters, search, sort]);
  return { rows, options, filters, setFilters, search, setSearch, sort, setSort };
}

export function FindingsTable({
  findings,
  selected,
  onSelect,
}: {
  findings: Finding[];
  selected: string | null;
  onSelect: (key: string | null) => void;
}) {
  const t = useFiltered(findings);
  const scroller = useRef<HTMLDivElement>(null);
  const v = useVirtualizer({ count: t.rows.length, getScrollElement: () => scroller.current, estimateSize: () => ROW_H, overscan: 10 });
  const active = Math.max(0, t.rows.findIndex((f) => f.identity_key === selected));

  const move = (i: number) => {
    const idx = Math.min(Math.max(i, 0), t.rows.length - 1);
    if (idx < 0) return;
    onSelect(t.rows[idx].identity_key);
    v.scrollToIndex(idx);
  };
  const onKey = (e: KeyboardEvent) => {
    const keys: Record<string, () => void> = {
      ArrowDown: () => move(selected ? active + 1 : 0),
      ArrowUp: () => move(active - 1),
      Home: () => move(0),
      End: () => move(t.rows.length - 1),
      Escape: () => onSelect(null),
    };
    if (keys[e.key]) {
      e.preventDefault();
      keys[e.key]();
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-end gap-2 border-b border-line p-2">
        {FILTERS.map((k) => (
          <label key={k} className="text-xs text-muted">
            <span className="block">{LABEL[k]}</span>
            <select
              className={`${input} max-w-44 text-fg`}
              value={t.filters[k] ?? ""}
              onChange={(e) => t.setFilters({ ...t.filters, [k]: e.target.value || undefined })}
            >
              <option value="">All</option>
              {t.options[k].map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </label>
        ))}
        <label className="text-xs text-muted">
          <span className="block">GlobalId or name</span>
          <input type="search" className={`${input} w-56 text-fg`} value={t.search} onChange={(e) => t.setSearch(e.target.value)} />
        </label>
        <span className="ml-auto pb-1.5 text-xs text-muted" aria-live="polite" data-testid="finding-count">
          {t.rows.length} of {findings.length} findings
        </span>
      </div>
      <div role="grid" aria-rowcount={t.rows.length + 1} aria-label="Findings" className="flex min-h-0 flex-1 flex-col text-sm">
        <div role="row" className="flex border-b border-line bg-raised text-xs text-muted">
          {COLS.map(([key, label, w]) => {
            const on = t.sort.key === key;
            return (
              <div key={key} role="columnheader" aria-sort={on ? (t.sort.dir === 1 ? "ascending" : "descending") : "none"} className={`${w} shrink-0`}>
                <button
                  className="w-full cursor-pointer px-2 py-1.5 text-left font-medium hover:text-fg"
                  onClick={() => t.setSort({ key, dir: on ? (-t.sort.dir as 1 | -1) : 1 })}
                >
                  {label} {on ? (t.sort.dir === 1 ? "▲" : "▼") : ""}
                </button>
              </div>
            );
          })}
        </div>
        {t.rows.length === 0 ? (
          <Empty>{findings.length === 0 ? "No findings reported for this audit." : "No findings match the filters."}</Empty>
        ) : (
          <div
            ref={scroller}
            tabIndex={0}
            onKeyDown={onKey}
            aria-activedescendant={selected ? `f-${selected}` : undefined}
            className="relative min-h-64 flex-1 overflow-auto"
          >
            <div style={{ height: v.getTotalSize() }} className="relative">
              {v.getVirtualItems().map((it) => {
                const f = t.rows[it.index];
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
                    <Cell w="w-28">{f.element_name ?? "—"}</Cell>
                    <Cell w="w-52" mono>{f.global_id ?? "model"}</Cell>
                    <Cell w="flex-1">{f.message}</Cell>
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

function Cell({ w, mono, children }: { w: string; mono?: boolean; children: ReactNode }) {
  return (
    <div role="gridcell" className={`${w} min-w-0 shrink-0 truncate px-2 ${mono ? "font-mono text-xs" : ""}`}>
      {children}
    </div>
  );
}
