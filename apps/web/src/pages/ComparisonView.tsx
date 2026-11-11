import { ChevronDown, Download, Layers, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Change, Comparison, FindingEvent, RevisionSummary } from "../api/client";
import { useChanges, useEvents } from "../api/queries";
import { btn, fmt, Panel, Q, Severity, tokenColor } from "../ui";
import { useFocus, Viewport, type Viewer } from "../viewer/Viewport";
import { Waterfall } from "./Waterfall";
import { backendLang, tokenLabel, useT } from "../i18n";

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
  const { t } = useT();
  const resolvedByRemoval = events.data?.filter((e) => e.event === "resolved" && e.note === "element_removed").length ?? 0;
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <ReportExport auditId={c.head_audit_run_id} comparisonId={c.id} />
      </div>
      <Banners c={c} />
      <Kpis c={c} seqs={seqs} resolvedByRemoval={resolvedByRemoval} />
      <div className="grid gap-4 lg:grid-cols-[1fr_440px]">
        <Panel title={t("Finding events")}>
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
                  {focus === "no_geometry" ? t("Element has no renderable geometry.") : t("Element is not in r{n}.", { n: seqs[1] })}
                </div>
              )
            }
          />
          {changes.data && events.data && <ShowChanges viewer={viewer} changes={changes.data} events={events.data} unstable={c.identity_unstable} />}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t("Health index change by dimension")}>
          <Waterfall mhi={s.mhi} seqs={seqs} />
        </Panel>
        <Panel title={t("Changes by class")}>
          <ByClass byClass={s.changes_by_class} />
        </Panel>
      </div>
      {!c.identity_unstable && (
        <>
          <Panel title={t("Why findings moved")}>
            <Impact impact={s.impact} onPick={setTarget} />
          </Panel>
          <Panel title={t("Property changes")}>
            <Q q={changes} rows={6}>
              {(cs: Change[]) => <PropertyChanges changes={cs} onPick={setTarget} />}
            </Q>
          </Panel>
        </>
      )}
    </div>
  );
}

function Banners({ c }: { c: Comparison }) {
  const s = c.summary_json;
  const { t } = useT();
  const notes = [
    c.identity_unstable &&
      t("GlobalIds look regenerated for {classes}. Element continuity cannot be trusted: all finding events are uncertain and per-element changes are hidden.", { classes: s.unstable_classes.join(", ") }),
    s.ids_mismatch && t("The two audits used different IDS files; IDS events are uncertain."),
    s.ruleset_mismatch && t("The two audits used different rule sets; affected events are uncertain."),
  ].filter(Boolean) as string[];
  return notes.map((n) => (
    <div key={n} role="alert" className="flex items-start gap-2 rounded border border-sev-medium bg-panel px-3 py-2 text-sm">
      <TriangleAlert size={16} className="mt-0.5 shrink-0 text-sev-medium" aria-hidden /> {n}
    </div>
  ));
}

function Kpis({ c, seqs, resolvedByRemoval }: { c: Comparison; seqs: [number, number]; resolvedByRemoval: number }) {
  const { mhi, changes, events } = c.summary_json;
  const { t } = useT();
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
      {kpi(t("Health index"), mhi.delta == null ? "—" : `${mhi.delta > 0 ? "+" : ""}${fmt(mhi.delta)}`, `r${seqs[0]} ${fmt(mhi.base)} → r${seqs[1]} ${fmt(mhi.head)}`, tone)}
      {kpi(t("Elements changed"), String((changes.added ?? 0) + (changes.removed ?? 0) + (changes.modified ?? 0)), t("+{a} added · −{r} removed · {m} modified", { a: changes.added ?? 0, r: changes.removed ?? 0, m: changes.modified ?? 0 }))}
      {kpi(t("Recurring findings"), String(events.recurring ?? 0), t("fixed before, back again"), events.recurring ? "text-sev-critical" : "")}
      {kpi(
        t("New / resolved"),
        `${events.new ?? 0} / ${events.resolved ?? 0}`,
        // an element deleted is not an issue fixed: a reviewer must not read one as the other
        (resolvedByRemoval ? t("{n} resolved only because the element was removed", { n: resolvedByRemoval }) + " · " : "") +
          t("{p} persistent · {u} uncertain", { p: events.persistent ?? 0, u: events.uncertain ?? 0 }),
      )}
    </dl>
  );
}

function EventGroups({ events, selected, onPick }: { events: FindingEvent[]; selected: string | null; onPick: (g: string) => void }) {
  const persistent = events.filter((e) => e.event === "persistent");
  const { t } = useT();
  const row = (e: FindingEvent) => (
    <li key={`${e.event}-${e.identity_key}`}>
      <button
        className={`flex w-full items-center gap-3 rounded px-1 py-1 text-left text-sm hover:bg-raised disabled:cursor-default ${e.global_id && e.global_id === selected ? "bg-raised" : ""}`}
        disabled={!e.global_id}
        onClick={() => e.global_id && onPick(e.global_id)}
        aria-label={`${t(e.event)} ${e.rule_id} ${e.element_name ?? e.global_id ?? t("model")}`}
      >
        <span className={`w-20 ${EVENT_TEXT[e.event] ?? ""}`}>{t(e.event)}</span>
        <span className="w-28 truncate">{e.rule_id}</span>
        <span className="flex-1 truncate">{e.element_name ?? (e.global_id ? "—" : t("model"))}</span>
        <Severity value={e.severity} />
      </button>
      {e.note && <p className="pl-24 text-xs text-muted">{tokenLabel(t, e.note)}</p>}
    </li>
  );
  if (events.length === persistent.length) return <p className="text-sm text-muted">{t("No new, resolved or recurring findings.")}</p>;
  return (
    <div className="space-y-3">
      {EVENT_ORDER.map((k) => {
        const group = events.filter((e) => e.event === k);
        return group.length > 0 && (
          <section key={k} aria-label={t("{event} findings", { event: t(k) })}>
            <h3 className={`text-xs uppercase tracking-wide ${EVENT_TEXT[k]}`}>
              {t(k)} ({group.length})
            </h3>
            <ul>{group.map(row)}</ul>
          </section>
        );
      })}
      {persistent.length > 0 && (
        <details>
          <summary className="cursor-pointer text-xs uppercase tracking-wide text-muted">
            {t("persistent")} ({persistent.length})
          </summary>
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
  const { t } = useT();

  useEffect(() => {
    if (!viewer) return;
    const map = new Map<string, string[]>();
    if (on) CHANGE_LEGEND.forEach(([token], i) => groups[i].length && map.set(tokenColor(token), groups[i]));
    viewer.highlight(map);
  }, [viewer, on, groups]);

  return (
    <div className="flex flex-wrap items-center gap-3 text-xs">
      <button className={btn} aria-pressed={on} disabled={!viewer} onClick={() => setOn(!on)}>
        <Layers size={14} aria-hidden /> {on ? t("Hide changes") : t("Show changes")}
      </button>
      {on &&
        CHANGE_LEGEND.map(([token, label], i) => (
          <span key={label} className="inline-flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-sm" style={{ background: `var(--color-${token})` }} aria-hidden />
            {t(label)} {groups[i].length}
          </span>
        ))}
      {on && removed > 0 && <span className="text-muted">{t("{n} removed (not in this file)", { n: removed })}</span>}
    </div>
  );
}

function ByClass({ byClass }: { byClass: Record<string, Record<string, number>> }) {
  const rows = Object.entries(byClass);
  const { t } = useT();
  if (rows.length === 0) return <p className="text-sm text-muted">{t("No element changes.")}</p>;
  return (
    <table className="w-full text-sm">
      <thead className="text-xs text-muted">
        <tr>
          <th className="text-left font-normal">{t("Class")}</th>
          {["added", "removed", "modified"].map((k) => (
            <th key={k} className="text-right font-normal">{t(k)}</th>
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
  const { t } = useT();
  if (impact.length === 0) return <p className="text-sm text-muted">{t("No finding moved because of an element change.")}</p>;
  return (
    <ul className="space-y-1 text-sm">
      {impact.map((i) => (
        <li key={`${i.global_id}-${i.rule_id}`}>
          <button className="text-left hover:underline" onClick={() => onPick(i.global_id)}>
            <span className="font-medium">{i.element_name ?? i.global_id}</span>: {i.paths.join(", ")} {t("changed")} →{" "}
            <span className={EVENT_TEXT[i.event] ?? ""}>
              {i.rule_id} {t(i.event)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

const show = (v: unknown) => (v == null ? "—" : Array.isArray(v) ? v.join(", ") || "∅" : String(v));

function PropertyChanges({ changes, onPick }: { changes: Change[]; onPick: (g: string) => void }) {
  const { t } = useT();
  if (changes.length === 0) return <p className="text-sm text-muted">{t("No element changes.")}</p>;
  return (
    <div className="max-h-96 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-panel text-xs text-muted">
          <tr>
            {["Change", "Class", "GlobalId", "Path", "Old", "New"].map((h) => (
              <th key={h} className="py-1 pr-3 text-left font-normal">
                {t(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {changes.map((x, i) => (
            <tr key={i} className="border-t border-line">
              <td className="py-1 pr-3">{t(x.kind)}</td>
              <td className="py-1 pr-3">{x.ifc_class}</td>
              <td className="py-1 pr-3 font-mono text-xs">
                <button className="hover:underline" onClick={() => onPick(x.global_id)} disabled={x.kind === "removed"}>
                  {x.global_id}
                </button>
              </td>
              <td className="py-1 pr-3 font-mono text-xs">{x.path ?? "—"}</td>
              <td className="py-1 pr-3">{show(x.old)}</td>
              <td className="py-1">{show(x.new)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Report downloads for an audit, with the comparison it heads when given. */
export function ReportExport({ auditId, comparisonId }: { auditId: number | null; comparisonId?: number }) {
  const { t, lang } = useT();
  if (auditId == null) return null;
  const query = (fmt: string) => `format=${fmt}&lang=${backendLang(lang)}${comparisonId == null ? "" : `&comparison_id=${comparisonId}`}`;
  // plain form POSTs: the browser handles download / new tab, no blob plumbing
  const form = (fmt: string, label: string) => (
    <form method="post" action={`/api/v1/audits/${auditId}/reports?${query(fmt)}`} target={fmt === "html" ? "_blank" : undefined}>
      <button className="w-full cursor-pointer px-3 py-1.5 text-left hover:bg-raised" type="submit">
        {label}
      </button>
    </form>
  );
  return (
    <details className="relative text-sm">
      <summary className={`${btn} list-none`}>
        <Download size={14} aria-hidden /> {t("Export report")} <ChevronDown size={14} aria-hidden />
      </summary>
      <div className="absolute right-0 z-20 mt-1 w-56 rounded border border-line bg-panel py-1 shadow-lg">
        {form("html", t("Printable HTML"))}
        {form("csv", t("Findings CSV (Excel)"))}
        {form("bcf", t("BCF 3.0 issues (Revit, Solibri, BIMcollab)"))}
        {form("bcf21", t("BCF 2.1 for Revit add-ins and Autodesk Construction Cloud"))}
        {form("json", "JSON")}
      </div>
    </details>
  );
}
