import { Download, Layers, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Change, Comparison, FindingEvent, RevisionSummary } from "../api/client";
import { useChanges, useEvents } from "../api/queries";
import { btn, fmt, Panel, Q, Severity, tokenColor } from "../ui";
import { useFocus, Viewport, type Viewer } from "../viewer/Viewport";
import { Waterfall } from "./Waterfall";

// recurring first: a finding that was fixed and came back is the regression reviewers miss
const EVENT_ORDER = ["recurring", "new", "changed", "uncertain", "resolved"] as const;
const EVENT_TEXT: Record<string, string> = {
  recurring: "text-sev-critical font-semibold",
  new: "text-sev-high",
  changed: "text-sev-medium",
  uncertain: "text-ne",
  resolved: "text-ok",
};

export function ComparisonView({ c, head, seqs }: { c: Comparison; head: RevisionSummary; seqs: [number, number] }) {
  const s = c.summary_json;
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const [target, setTarget] = useState<string | null>(null);
  const focus = useFocus(viewer, target);
  const events = useEvents(c.id);
  const changes = useChanges(c.id);
  return (
    <div className="space-y-4">
      <Banners c={c} />
      <Kpis c={c} seqs={seqs} />
      <div className="grid gap-4 lg:grid-cols-[1fr_440px]">
        <Panel title="Finding events">
          <Q q={events} rows={6}>
            {(es: FindingEvent[]) => <EventGroups events={es} selected={target} onPick={setTarget} />}
          </Q>
        </Panel>
        <div className="space-y-2">
          <Viewport
            className="h-80"
            fileUrl={`/api/v1/revisions/${head.id}/file`}
            sha={head.file_sha256}
            onViewer={setViewer}
            overlay={
              focus && focus !== "ok" && (
                <div role="status" className="absolute inset-x-2 bottom-2 rounded border border-line bg-raised px-2 py-1 text-xs">
                  {focus === "no_geometry" ? "Element has no renderable geometry." : `Element is not in r${seqs[1]}.`}
                </div>
              )
            }
          />
          {changes.data && events.data && <ShowChanges viewer={viewer} changes={changes.data} events={events.data} unstable={c.identity_unstable} />}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Health index change by dimension">
          <Waterfall mhi={s.mhi} seqs={seqs} />
        </Panel>
        <Panel title="Changes by class">
          <ByClass byClass={s.changes_by_class} />
        </Panel>
      </div>
      {!c.identity_unstable && (
        <>
          <Panel title="Why findings moved">
            <Impact impact={s.impact} onPick={setTarget} />
          </Panel>
          <Panel title="Property changes">
            <Q q={changes} rows={6}>
              {(cs: Change[]) => <PropertyChanges changes={cs} onPick={setTarget} />}
            </Q>
          </Panel>
        </>
      )}
      <ReportExport auditId={c.head_audit_run_id} comparisonId={c.id} />
    </div>
  );
}

function Banners({ c }: { c: Comparison }) {
  const s = c.summary_json;
  const notes = [
    c.identity_unstable &&
      `GlobalIds look regenerated for ${s.unstable_classes.join(", ")}. Element continuity cannot be trusted: all finding events are uncertain and per-element changes are hidden.`,
    s.ids_mismatch && "The two audits used different IDS files; IDS events are uncertain.",
    s.ruleset_mismatch && "The two audits used different rule sets; affected events are uncertain.",
  ].filter(Boolean) as string[];
  return notes.map((n) => (
    <div key={n} role="alert" className="flex items-start gap-2 rounded border border-sev-medium bg-panel px-3 py-2 text-sm">
      <TriangleAlert size={16} className="mt-0.5 shrink-0 text-sev-medium" aria-hidden /> {n}
    </div>
  ));
}

function Kpis({ c, seqs }: { c: Comparison; seqs: [number, number] }) {
  const { mhi, changes, events } = c.summary_json;
  const tone = mhi.delta == null || Math.abs(mhi.delta) < 0.05 ? "" : mhi.delta > 0 ? "text-ok" : "text-sev-high";
  const kpi = (label: string, value: string, sub: string, cls = "") => (
    <div className="rounded border border-line bg-raised px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={`text-xl font-semibold ${cls}`}>{value}</dd>
      <dd className="text-xs text-muted">{sub}</dd>
    </div>
  );
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {kpi("Health index", mhi.delta == null ? "—" : `${mhi.delta > 0 ? "+" : ""}${fmt(mhi.delta)}`, `r${seqs[0]} ${fmt(mhi.base)} → r${seqs[1]} ${fmt(mhi.head)}`, tone)}
      {kpi("Elements changed", String((changes.added ?? 0) + (changes.removed ?? 0) + (changes.modified ?? 0)), `+${changes.added ?? 0} added · −${changes.removed ?? 0} removed · ${changes.modified ?? 0} modified`)}
      {kpi("Recurring findings", String(events.recurring ?? 0), "fixed before, back again", events.recurring ? "text-sev-critical" : "")}
      {kpi("New / resolved", `${events.new ?? 0} / ${events.resolved ?? 0}`, `${events.persistent ?? 0} persistent · ${events.uncertain ?? 0} uncertain`)}
    </dl>
  );
}

function EventGroups({ events, selected, onPick }: { events: FindingEvent[]; selected: string | null; onPick: (g: string) => void }) {
  const persistent = events.filter((e) => e.event === "persistent");
  const row = (e: FindingEvent) => (
    <li key={`${e.event}-${e.identity_key}`}>
      <button
        className={`flex w-full items-center gap-3 rounded px-1 py-1 text-left text-sm hover:bg-raised disabled:cursor-default ${e.global_id && e.global_id === selected ? "bg-raised" : ""}`}
        disabled={!e.global_id}
        onClick={() => e.global_id && onPick(e.global_id)}
        aria-label={`${e.event} ${e.rule_id} ${e.element_name ?? e.global_id ?? "model"}`}
      >
        <span className={`w-20 ${EVENT_TEXT[e.event] ?? ""}`}>{e.event}</span>
        <span className="w-28 truncate">{e.rule_id}</span>
        <span className="flex-1 truncate">{e.element_name ?? (e.global_id ? "—" : "model")}</span>
        <Severity value={e.severity} />
      </button>
      {e.note && <p className="pl-24 text-xs text-muted">{e.note}</p>}
    </li>
  );
  if (events.length === persistent.length) return <p className="text-sm text-muted">No new, resolved or recurring findings.</p>;
  return (
    <div className="space-y-3">
      {EVENT_ORDER.map((k) => {
        const group = events.filter((e) => e.event === k);
        return group.length > 0 && (
          <section key={k} aria-label={`${k} findings`}>
            <h3 className={`text-xs uppercase tracking-wide ${EVENT_TEXT[k]}`}>{k} ({group.length})</h3>
            <ul>{group.map(row)}</ul>
          </section>
        );
      })}
      {persistent.length > 0 && (
        <details>
          <summary className="cursor-pointer text-xs uppercase tracking-wide text-muted">persistent ({persistent.length})</summary>
          <ul>{persistent.map(row)}</ul>
        </details>
      )}
    </div>
  );
}

const CHANGE_LEGEND = [
  ["ok", "added"],
  ["accent", "modified"],
  ["sev-high", "new finding"],
  ["sev-critical", "recurring finding"],
] as const;

function ShowChanges({ viewer, changes, events, unstable }: { viewer: Viewer | null; changes: Change[]; events: FindingEvent[]; unstable: boolean }) {
  const [on, setOn] = useState(false);
  const groups = useMemo(() => {
    const uniq = (xs: (string | null)[]) => [...new Set(xs.filter((x): x is string => x != null))];
    const kind = (k: string) => uniq(changes.filter((x) => x.kind === k).map((x) => x.global_id));
    const ev = (k: string) => uniq(events.filter((e) => e.event === k).map((e) => e.global_id));
    // later groups paint over earlier ones: findings matter more than the edit that caused them
    return [kind("added"), unstable ? [] : kind("modified"), ev("new"), ev("recurring")];
  }, [changes, events, unstable]);
  const removed = changes.filter((x) => x.kind === "removed").length;

  useEffect(() => {
    if (!viewer) return;
    const map = new Map<string, string[]>();
    if (on) CHANGE_LEGEND.forEach(([token], i) => groups[i].length && map.set(tokenColor(token), groups[i]));
    viewer.highlight(map);
  }, [viewer, on, groups]);

  return (
    <div className="flex flex-wrap items-center gap-3 text-xs">
      <button className={btn} aria-pressed={on} disabled={!viewer} onClick={() => setOn(!on)}>
        <Layers size={14} aria-hidden /> {on ? "Hide changes" : "Show changes"}
      </button>
      {on &&
        CHANGE_LEGEND.map(([token, label], i) => (
          <span key={label} className="inline-flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-sm" style={{ background: `var(--color-${token})` }} aria-hidden />
            {label} {groups[i].length}
          </span>
        ))}
      {on && removed > 0 && <span className="text-muted">{removed} removed (not in this file)</span>}
    </div>
  );
}

function ByClass({ byClass }: { byClass: Record<string, Record<string, number>> }) {
  const rows = Object.entries(byClass);
  if (rows.length === 0) return <p className="text-sm text-muted">No element changes.</p>;
  return (
    <table className="w-full text-sm">
      <thead className="text-xs text-muted">
        <tr>
          <th className="text-left font-normal">Class</th>
          {["added", "removed", "modified"].map((k) => (
            <th key={k} className="text-right font-normal">{k}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(([cls, k]) => (
          <tr key={cls} className="border-t border-line">
            <td className="py-1">{cls}</td>
            <td className="py-1 text-right tabular-nums">{k.added ?? 0}</td>
            <td className="py-1 text-right tabular-nums">{k.removed ?? 0}</td>
            <td className="py-1 text-right tabular-nums">{k.modified ?? 0}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Impact({ impact, onPick }: { impact: Comparison["summary_json"]["impact"]; onPick: (g: string) => void }) {
  if (impact.length === 0) return <p className="text-sm text-muted">No finding moved because of an element change.</p>;
  return (
    <ul className="space-y-1 text-sm">
      {impact.map((i) => (
        <li key={`${i.global_id}-${i.rule_id}`}>
          <button className="text-left hover:underline" onClick={() => onPick(i.global_id)}>
            <span className="font-medium">{i.element_name ?? i.global_id}</span>: {i.paths.join(", ")} changed →{" "}
            <span className={EVENT_TEXT[i.event] ?? ""}>{i.rule_id} {i.event}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

const show = (v: unknown) => (v == null ? "—" : Array.isArray(v) ? v.join(", ") || "none" : String(v));

function PropertyChanges({ changes, onPick }: { changes: Change[]; onPick: (g: string) => void }) {
  if (changes.length === 0) return <p className="text-sm text-muted">No element changes.</p>;
  return (
    <div className="max-h-96 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-panel text-xs text-muted">
          <tr>
            {["Change", "Class", "GlobalId", "Path", "Old", "New"].map((h) => (
              <th key={h} className="py-1 text-left font-normal">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {changes.map((x, i) => (
            <tr key={i} className="border-t border-line">
              <td className="py-1">{x.kind}</td>
              <td className="py-1">{x.ifc_class}</td>
              <td className="py-1 font-mono text-xs">
                <button className="hover:underline" onClick={() => onPick(x.global_id)} disabled={x.kind === "removed"}>
                  {x.global_id}
                </button>
              </td>
              <td className="py-1 font-mono text-xs">{x.path ?? "—"}</td>
              <td className="py-1">{show(x.old)}</td>
              <td className="py-1">{show(x.new)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReportExport({ auditId, comparisonId }: { auditId: number | null; comparisonId: number }) {
  if (auditId == null) return null;
  // plain form POSTs: the browser handles download / new tab, no blob plumbing
  const form = (fmt: string, label: string) => (
    <form method="post" action={`/api/v1/audits/${auditId}/reports?format=${fmt}&comparison_id=${comparisonId}`} target={fmt === "html" ? "_blank" : undefined}>
      <button className={btn} type="submit">
        <Download size={14} aria-hidden /> {label}
      </button>
    </form>
  );
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-muted">Report for this comparison:</span>
      {form("html", "Printable HTML")}
      {form("json", "JSON")}
      {form("csv", "Findings CSV")}
    </div>
  );
}
