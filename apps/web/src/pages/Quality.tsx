import { Boxes, Highlighter, ShieldAlert, X } from "lucide-react";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import type { AuditSummary, Dimension, Finding, Mhi, RuleMeta } from "../api/client";
import { useAuditSummary, useFindings, useRevision } from "../api/queries";
import { btn, Empty, fmt, Panel, Q, SEVERITIES, Severity, Status, tokenColor } from "../ui";
import { useFocus, Viewport, type FocusResult, type Viewer } from "../viewer/Viewport";
import { FindingsTable } from "./FindingsTable";

export function Quality() {
  const revisionId = Number(useParams().revisionId);
  const rev = useRevision(revisionId);
  const auditId = rev.data?.latest_audit_id;
  const summary = useAuditSummary(auditId);
  const findings = useFindings(auditId);
  const [selected, setSelected] = useState<string | null>(useSearchParams()[0].get("finding"));
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const finding = findings.data?.find((f) => f.identity_key === selected);
  const focus = useFocus(viewer, finding?.global_id);

  if (rev.data && auditId == null) return <Empty>This revision has not been audited yet.</Empty>;
  return (
    <div className="flex h-[calc(100dvh-4.5rem)] flex-col gap-3">
      <div className="flex items-baseline gap-3">
        <h1 className="text-lg font-semibold">Quality Center</h1>
        {rev.data && (
          <span className="text-sm text-muted">
            r{rev.data.seq} · {String(rev.data.metadata.project_name ?? "")} · audit {auditId}
          </span>
        )}
        <Link className={`${btn} ml-auto`} to={`/revisions/${revisionId}/explorer`}>
          <Boxes size={14} aria-hidden /> Model Explorer
        </Link>
      </div>
      <Q q={summary} rows={4}>
        {(s: AuditSummary) => <HealthHeader mhi={s.mhi} />}
      </Q>
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[1fr_400px]">
        <section className="flex min-h-0 flex-col rounded border border-line bg-panel">
          <Q q={findings} rows={8}>
            {(fs: Finding[]) => (
              <FindingsTable findings={fs} selected={selected} onSelect={setSelected} toolbar={(rows) => <HighlightAll viewer={viewer} rows={rows} />} />
            )}
          </Q>
        </section>
        <aside className="flex min-h-0 flex-col gap-3">
          {rev.data && (
            <Viewport
              className="h-64 shrink-0"
              fileUrl={`/api/v1/revisions/${revisionId}/file`}
              sha={rev.data.file_sha256}
              onViewer={setViewer}
              overlay={finding && <FocusNote result={focus} modelLevel={finding.global_id == null} />}
            />
          )}
          {finding && <FindingDetail f={finding} rule={summary.data?.rules.find((r) => r.id === finding.rule_id)} onClose={() => setSelected(null)} />}
        </aside>
      </div>
    </div>
  );
}

const NOTE: Record<FocusResult, string | null> = {
  ok: null,
  no_geometry: "Element has no renderable geometry.",
  not_found: "Element not found in the 3D model.",
};

function FocusNote({ result, modelLevel }: { result: FocusResult | null; modelLevel: boolean }) {
  const text = modelLevel ? "Model-level finding: no element to show." : result && NOTE[result];
  if (!text) return null;
  return (
    <div role="status" className="absolute inset-x-2 bottom-2 rounded border border-line bg-raised px-2 py-1 text-xs">
      {text}
    </div>
  );
}

/** Colour every element in the current filter by its worst severity; toggle off clears. */
function HighlightAll({ viewer, rows }: { viewer: Viewer | null; rows: Finding[] }) {
  const [on, setOn] = useState(false);
  const toggle = async () => {
    if (!viewer) return;
    const groups = new Map<string, string[]>();
    if (!on) {
      const worst = new Map<string, number>();
      for (const f of rows) {
        if (!f.global_id || f.status === "pass" || f.status === "not_applicable") continue;
        const rank = SEVERITIES.indexOf(f.severity as (typeof SEVERITIES)[number]);
        worst.set(f.global_id, Math.min(rank, worst.get(f.global_id) ?? rank));
      }
      for (const [gid, rank] of worst) {
        const color = tokenColor(`sev-${SEVERITIES[rank]}`);
        groups.set(color, [...(groups.get(color) ?? []), gid]);
      }
    }
    await viewer.highlight(groups);
    setOn(!on);
  };
  return (
    <button className={`${btn} mb-0.5`} onClick={toggle} disabled={!viewer} aria-pressed={on}>
      <Highlighter size={14} aria-hidden /> {on ? "Clear highlight" : "Highlight in 3D"}
    </button>
  );
}

function HealthHeader({ mhi }: { mhi: Mhi }) {
  const dims = Object.entries(mhi.dimensions);
  return (
    <div className="grid gap-3 lg:grid-cols-[220px_1fr]">
      <div className="rounded border border-line bg-panel px-4 py-3">
        <div className="text-xs text-muted">Model Health Index</div>
        <div className="text-4xl font-semibold" data-testid="mhi-score">
          {fmt(mhi.score)}
        </div>
        <div className="mt-1 text-xs text-muted">coverage {fmt(mhi.coverage, 0)}% · config {mhi.config_version}</div>
        {mhi.blocked && (
          <div className="mt-2 inline-flex items-center gap-1 rounded border border-sev-critical px-2 py-0.5 text-xs text-sev-critical">
            <ShieldAlert size={12} aria-hidden /> blocked by {mhi.blocking.length} critical finding(s)
          </div>
        )}
        {mhi.notes.map((n) => (
          <p key={n} className="mt-1 text-xs text-muted">
            {n}
          </p>
        ))}
      </div>
      <Panel title="Dimensions">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted">
            <tr>
              {["Dimension", "Weight", "Score", "", "Pass", "Fail", "Warn", "Not eval.", "Error", "Contribution"].map((h, i) => (
                <th key={i} className={`py-0.5 font-medium ${i > 3 ? "text-right" : ""}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dims.map(([name, d]) => (
              <DimensionRow key={name} name={name} d={d} />
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}

function DimensionRow({ name, d }: { name: string; d: Dimension }) {
  const ne = d.score == null;
  return (
    <tr className="border-t border-line">
      <td className="py-1 pr-2">{name.replace(/_/g, " ")}</td>
      <td className="py-1 text-muted">{(d.weight * 100).toFixed(0)}%</td>
      <td className="py-1">{ne ? <Status value="not_evaluated" /> : fmt(d.score)}</td>
      <td className="w-1/4 py-1 pr-2">
        <ScoreBar d={d} />
      </td>
      <Num n={d.passed} />
      <Num n={d.failed} cls={d.failed ? "text-sev-critical" : ""} />
      <Num n={d.warnings} />
      <Num n={d.not_evaluated} cls="text-ne" />
      <Num n={d.errors} />
      <td className="py-1 text-right">{ne ? "—" : d.contribution.toFixed(1)}</td>
    </tr>
  );
}

/** Pass share in ok, fail share in red; a dimension with nothing evaluated is hatched, never red. */
function ScoreBar({ d }: { d: Dimension }) {
  const label = d.score == null ? "not evaluated" : `${fmt(d.score)} of 100`;
  return (
    <div role="img" aria-label={label} title={label} className={`flex h-2 overflow-hidden rounded-sm bg-raised ${d.score == null ? "hatch" : ""}`}>
      {d.score != null && (
        <>
          <div className="bg-ok" style={{ width: `${d.score}%` }} />
          <div className="bg-sev-critical" style={{ width: `${100 - d.score}%` }} />
        </>
      )}
    </div>
  );
}

const Num = ({ n, cls = "" }: { n: number; cls?: string }) => <td className={`py-1 text-right ${n ? cls : "text-muted"}`}>{n}</td>;

function FindingDetail({ f, rule, onClose }: { f: Finding; rule?: RuleMeta; onClose: () => void }) {
  return (
    <section aria-label="Finding detail" className="min-h-0 flex-1 overflow-auto rounded border border-line bg-panel">
      <header className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-sm font-semibold">
          {f.rule_id} <span className="font-normal text-muted">v{f.rule_version}</span>
        </h2>
        <button className={btn} onClick={onClose} aria-label="Close finding detail">
          <X size={14} aria-hidden />
        </button>
      </header>
      <div className="space-y-3 p-3 text-sm">
        {rule && (
          <div>
            <div className="font-medium">{rule.name}</div>
            <p className="text-muted">{rule.description}</p>
          </div>
        )}
        <dl className="grid grid-cols-[96px_1fr] gap-x-2 gap-y-1">
          <dt className="text-muted">Status</dt>
          <dd><Status value={f.status} /></dd>
          <dt className="text-muted">Severity</dt>
          <dd><Severity value={f.severity} /></dd>
          <dt className="text-muted">Element</dt>
          <dd>{f.ifc_class ? `${f.ifc_class} ${f.element_name ?? ""}` : "model-level"}</dd>
          <dt className="text-muted">GlobalId</dt>
          <dd className="font-mono text-xs">{f.global_id ?? "—"}</dd>
          <dt className="text-muted">Expected</dt>
          <dd>{f.expected ?? "—"}</dd>
          <dt className="text-muted">Actual</dt>
          <dd>{f.actual ?? "—"}</dd>
          <dt className="text-muted">Issue key</dt>
          <dd className="font-mono text-xs">{f.issue_key}</dd>
        </dl>
        <div>
          <div className="mb-1 text-xs text-muted">Evidence</div>
          <pre className="overflow-auto rounded bg-bg p-2 font-mono text-xs">{JSON.stringify(f.evidence, null, 2)}</pre>
        </div>
      </div>
    </section>
  );
}
