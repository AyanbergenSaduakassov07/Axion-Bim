import { CalendarX2, CircleCheck, CircleDot, UserRoundX } from "lucide-react";
import type { ReactNode } from "react";
import type { Dashboard as Data } from "../api/client";
import { useDashboard } from "../api/queries";
import { useT } from "../i18n";
import { date, fmt, Panel, Q } from "../ui";

/** Project at a glance for managers: issue KPIs, MHI trend per model, where the open work sits (D-33). */
export function Dashboard({ projectId }: { projectId: number }) {
  const q = useDashboard(projectId);
  const { t } = useT();
  return (
    <Panel title={t("Project dashboard")}>
      <Q q={q} rows={4}>
        {(d: Data) => <Body d={d} />}
      </Q>
    </Panel>
  );
}

function Body({ d }: { d: Data }) {
  const { t } = useT();
  const s = d.issues.states;
  const active = s.open + s.in_progress + s.disputed;
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi icon={<CircleDot size={14} aria-hidden />} label={t("Active issues")} value={active} sub={t("{a} in progress · {b} disputed", { a: s.in_progress, b: s.disputed })} />
        <Kpi icon={<CalendarX2 size={14} aria-hidden className="text-sev-critical" />} label={t("Overdue")} value={d.issues.overdue} alert={d.issues.overdue > 0} sub={t("past due date, not closed")} />
        <Kpi icon={<UserRoundX size={14} aria-hidden />} label={t("Unassigned")} value={d.issues.unassigned} sub={t("active issues without an owner")} />
        <Kpi icon={<CircleCheck size={14} aria-hidden className="text-ok" />} label={t("Resolved")} value={s.accepted + s.closed} sub={t("{a} accepted · {b} closed", { a: s.accepted, b: s.closed })} />
      </dl>
      <div className="grid gap-4 lg:grid-cols-3">
        <section>
          <h3 className="mb-2 text-xs font-medium text-muted">{t("Model Health Index by revision")}</h3>
          <ul className="space-y-3">
            {d.models.map((m) => (
              <li key={m.model_id}>
                <div className="flex items-baseline justify-between text-sm">
                  <span className="font-medium">{m.name}</span>
                  <span className="text-muted">{t("{n} findings", { n: m.findings })}</span>
                </div>
                <Trend points={m.trend} />
              </li>
            ))}
          </ul>
        </section>
        <Bars
          title={t("Active issues by assignee")}
          empty={t("Nobody assigned yet. Assign issues in the Quality Center.")}
          rows={d.issues.by_assignee.map((a) => ({ label: a.assignee, n: a.active, note: a.overdue ? t("{n} overdue", { n: a.overdue }) : undefined }))}
        />
        <Bars title={t("Active issues by rule")} empty={t("No active issues.")} rows={d.issues.by_rule.slice(0, 8).map((r) => ({ label: r.rule_id, n: r.active }))} />
      </div>
    </div>
  );
}

function Kpi({ icon, label, value, sub, alert }: { icon: ReactNode; label: string; value: number; sub: string; alert?: boolean }) {
  return (
    <div className={`rounded border bg-raised px-3 py-2 ${alert ? "border-sev-critical" : "border-line"}`}>
      <dt className="flex items-center gap-1.5 text-xs text-muted">
        {icon}
        {label}
      </dt>
      <dd className="text-2xl font-semibold tabular-nums">{fmt(value, 0)}</dd>
      <dd className="text-xs text-muted">{sub}</dd>
    </div>
  );
}

const W = 240;
const H = 56;
const PAD = 6;

/** MHI on a fixed 0-100 scale so models compare honestly; one dot per audited revision. */
function Trend({ points }: { points: Data["models"][number]["trend"] }) {
  const { t } = useT();
  const scored = points.filter((p) => p.score != null);
  if (scored.length === 0) return <p className="text-xs text-muted">{t("Not audited.")}</p>;
  const x = (i: number) => (scored.length === 1 ? W / 2 : PAD + (i * (W - 2 * PAD)) / (scored.length - 1));
  const y = (v: number) => PAD + ((100 - v) * (H - 2 * PAD)) / 100;
  const path = scored.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.score!)}`).join(" ");
  const last = scored.at(-1)!;
  return (
    <div className="flex items-center gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={t("Model Health Index by revision")}>
        <line x1={0} x2={W} y1={y(100)} y2={y(100)} className="stroke-line" strokeDasharray="2 3" />
        <line x1={0} x2={W} y1={y(0)} y2={y(0)} className="stroke-line" />
        <path d={path} fill="none" className="stroke-accent" strokeWidth={2} strokeLinejoin="round" />
        {scored.map((p, i) => (
          <g key={p.revision_id}>
            <circle cx={x(i)} cy={y(p.score!)} r={4} className="fill-accent stroke-panel" strokeWidth={2} />
            <circle cx={x(i)} cy={y(p.score!)} r={12} fill="transparent">
              <title>{`r${p.seq} · ${date(p.created_at)} · MHI ${fmt(p.score)}`}</title>
            </circle>
          </g>
        ))}
      </svg>
      <span className="w-12 text-right text-lg font-semibold tabular-nums">{fmt(last.score)}</span>
    </div>
  );
}

function Bars({ title, rows, empty }: { title: string; rows: { label: string; n: number; note?: string }[]; empty: string }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  return (
    <section>
      <h3 className="mb-2 text-xs font-medium text-muted">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-xs text-muted">{empty}</p>
      ) : (
        <ul className="space-y-1.5 text-sm">
          {rows.map((r) => (
            <li key={r.label} title={`${r.label}: ${r.n}`}>
              <div className="flex justify-between gap-2">
                <span className="truncate">{r.label}</span>
                <span className="shrink-0 tabular-nums">
                  {r.note && <span className="mr-2 text-xs font-medium text-sev-critical">{r.note}</span>}
                  {fmt(r.n, 0)}
                </span>
              </div>
              <div className="mt-0.5 h-1.5 rounded-full bg-raised">
                <div className="h-full rounded-full bg-accent" style={{ width: `${(100 * r.n) / max}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
