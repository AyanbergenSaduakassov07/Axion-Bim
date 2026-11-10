import { ShieldAlert, Upload } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router";
import type { Finding, Model, Revision, RevisionSummary } from "../api/client";
import { useAudits, useAuditSummary, useFindings, useModels, useProjects, useRevision, useRevisions } from "../api/queries";
import { btn, btnPrimary, bytes, date, fmt, Panel, Q, Severity, SEVERITIES } from "../ui";
import { CopilotPanel } from "../copilot/CopilotPanel";
import { NameForm } from "./Projects";
import { Dashboard } from "./Dashboard";
import { useT } from "../i18n";

export function Overview() {
  const projectId = Number(useParams().projectId);
  const [params, setParams] = useSearchParams();
  const project = useProjects().data?.find((p) => p.id === projectId);
  const models = useModels(projectId);
  const modelId = Number(params.get("model")) || models.data?.[0]?.id;
  const { t } = useT();

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <h1 className="text-lg font-semibold">{project?.name ?? t("Project {id}", { id: projectId })}</h1>
      <Dashboard projectId={projectId} />
      <Panel
        title={t("Models")}
        actions={
          <NameForm
            label={t("Model name")}
            placeholder={t("New model name, e.g. Architecture")}
            submit={t("Create model")}
            path={`/projects/${projectId}/models`}
            invalidate={["models", projectId]}
            onCreated={(id) => setParams({ model: String(id) })}
          />
        }
      >
        <Q q={models} empty={(d) => d.length === 0 && t("No models yet. A model holds the revisions of one discipline file, e.g. Architecture or Structure.")}>
          {(ms: Model[]) => (
            <div role="tablist" className="flex flex-wrap gap-2">
              {ms.map((m) => (
                <button
                  key={m.id}
                  role="tab"
                  aria-selected={m.id === modelId}
                  className={m.id === modelId ? btnPrimary : btn}
                  onClick={() => setParams({ model: String(m.id) })}
                >
                  {m.name}
                </button>
              ))}
            </div>
          )}
        </Q>
      </Panel>
      {modelId != null && <ModelOverview modelId={modelId} />}
      {modelId != null && <CopilotPanel projectId={projectId} />}
    </div>
  );
}

function ModelOverview({ modelId }: { modelId: number }) {
  const revisions = useRevisions(modelId);
  const latest = revisions.data?.at(-1);
  const { t } = useT();
  return (
    <>
      <div className="flex justify-end gap-2">
        <Link className={btnPrimary} to={`/models/${modelId}/upload`}>
          <Upload size={14} aria-hidden /> {t("Upload revision")}
        </Link>
        <Link className={btn} to={`/models/${modelId}/revisions`}>
          {t("Compare revisions")}
        </Link>
      </div>
      <Q q={revisions} empty={(d) => d.length === 0 && t("No revisions yet. Upload an IFC file to start.")}>
        {(revs: Revision[]) => (
          <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
            {latest && <LatestRevision revisionId={latest.id} />}
            <Panel title={t("Revision timeline")}>
              <ol className="space-y-1">
                {[...revs].reverse().map((r) => (
                  <TimelineRow key={r.id} r={r} />
                ))}
              </ol>
            </Panel>
          </div>
        )}
      </Q>
    </>
  );
}

// shortcut: one audits request per revision; add score to the revisions endpoint when timelines get long
function TimelineRow({ r }: { r: Revision }) {
  const a = useAudits(r.id).data?.[0];
  const { t } = useT();
  return (
    <li className="flex items-center gap-3 border-t border-line py-1.5 text-sm first:border-0">
      <span className="w-8 font-semibold">r{r.seq}</span>
      <span className="flex-1 text-muted">{date(r.created_at)}</span>
      <span className="w-14 text-right" title={t("Model Health Index")}>
        {fmt(a?.score)}
      </span>
      {a?.blocked && <ShieldAlert size={14} className="text-sev-critical" aria-label={t("blocked")} />}
      <Link className="text-accent hover:underline" to={`/revisions/${r.id}/quality`}>
        {t("Quality")}
      </Link>
    </li>
  );
}

function LatestRevision({ revisionId }: { revisionId: number }) {
  const rev = useRevision(revisionId);
  const { t } = useT();
  return (
    <Panel title={t("Latest revision")}>
      <Q q={rev} rows={6}>
        {(r: RevisionSummary) => <RevisionStats r={r} />}
      </Q>
    </Panel>
  );
}

function RevisionStats({ r }: { r: RevisionSummary }) {
  const summary = useAuditSummary(r.latest_audit_id);
  const findings = useFindings(r.latest_audit_id);
  const counts = Object.entries(r.class_counts as Record<string, number>).sort((a, b) => b[1] - a[1]);
  const elements = counts.reduce((s, [, n]) => s + n, 0);
  const mhi = summary.data?.mhi;
  const { t } = useT();
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label={t("Revision")} value={`r${r.seq}`} sub={`${r.schema_name} · ${bytes(r.file_size)}`} />
        <Stat label={t("Elements")} value={String(elements)} sub={t("{n} classes", { n: counts.length })} />
        <Stat label={t("Health index")} value={fmt(mhi?.score)} sub={mhi?.blocked ? t("blocked") : t("{n}% of checks ran", { n: fmt(mhi?.coverage, 0) })} />
        <Stat label={t("Findings")} value={findings.data ? String(findings.data.length) : "—"} sub={t("reported")} />
      </dl>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-1 text-xs font-medium text-muted">{t("Findings by severity")}</h3>
          <Q q={findings} empty={(d) => d.length === 0 && (r.latest_audit_id == null ? t("Not audited.") : t("No findings."))}>
            {(fs: Finding[]) => <SeverityCounts findings={fs} />}
          </Q>
        </div>
        <div>
          <h3 className="mb-1 text-xs font-medium text-muted">{t("Elements by class")}</h3>
          <table className="w-full text-sm">
            <tbody>
              {counts.map(([cls, n]) => (
                <tr key={cls} className="border-t border-line first:border-0">
                  <td className="py-1">{cls}</td>
                  <td className="py-1 text-right">{n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="flex gap-2">
        {r.latest_audit_id != null && (
          <Link className={btn} to={`/revisions/${r.id}/quality`}>
            {t("Open Quality Center")}
          </Link>
        )}
        <Link className={btn} to={`/revisions/${r.id}/explorer`}>
          {t("Open 3D model")}
        </Link>
        <Link className={btn} to={`/revisions/${r.id}/quantities`}>
          {t("Quantities")}
        </Link>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded border border-line bg-raised px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-xl font-semibold">{value}</dd>
      <dd className="text-xs text-muted">{sub}</dd>
    </div>
  );
}

function SeverityCounts({ findings }: { findings: Finding[] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {SEVERITIES.map((s) => (
          <tr key={s} className="border-t border-line first:border-0">
            <td className="py-1">
              <Severity value={s} />
            </td>
            <td className="py-1 text-right">{findings.filter((f) => f.severity === s).length}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
