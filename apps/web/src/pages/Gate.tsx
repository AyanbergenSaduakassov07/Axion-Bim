import { useState } from "react";
import type { Gate, GatePolicy } from "../api/client";
import { useGate, useGatePolicy, useSetGatePolicy } from "../api/queries";
import { tokenLabel, useT, type T } from "../i18n";
import { btn, fmt, input, Panel } from "../ui";

const BLOCK_SEVERITIES = ["critical", "high", "medium", "low"] as const;
export const TONE: Record<Gate["decision"], string> = {
  accepted: "border-ok text-ok",
  accepted_with_comments: "border-sev-medium text-sev-medium",
  rejected: "border-sev-critical text-sev-critical",
  undecided: "border-line text-muted",
};

export function decisionLabel(t: T, d: Gate["decision"]): string {
  if (d === "accepted") return t("Accepted");
  if (d === "accepted_with_comments") return t("Accepted with comments");
  if (d === "rejected") return t("Rejected");
  return t("Not decided");
}

function reasonText(t: T, r: Gate["reasons"][number], policy: GatePolicy): string {
  const n = r.n as number;
  switch (r.code) {
    case "blocking_findings":
      return t("{n} open findings at severity {severity} or above block acceptance.", { n, severity: tokenLabel(t, policy.block_severity) });
    case "score_below_minimum":
      return t("MHI {score} is below the project minimum of {minimum}.", { score: fmt(r.score as number), minimum: fmt(r.minimum as number, 0) });
    case "ids_not_evaluated":
      return t("No client requirements file (IDS) was checked, so the delivery cannot be accepted.");
    case "score_not_evaluated":
      return t("The MHI was not computed, so the delivery cannot be accepted.");
    case "open_findings":
      return t("{n} findings remain open.", { n });
    case "waived":
      return t("{n} findings were accepted as they are by the reviewer.", { n });
    default:
      return String(r.code);
  }
}

/** Delivery decision (D-36). Computed by the backend from findings, waivers and the project's gate policy. */
export function GateDecision({ auditId }: { auditId: number }) {
  const { t } = useT();
  const g = useGate(auditId).data;
  if (!g) return null;
  return (
    <div className="rounded border border-line bg-panel px-4 py-3" data-testid="gate">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs text-muted">{t("Delivery decision")}</span>
        <span className={`rounded border px-2 py-0.5 text-sm font-semibold ${TONE[g.decision]}`} data-testid="gate-decision">
          {decisionLabel(t, g.decision)}
        </span>
        <span className="text-xs text-muted">
          {t("Policy: MHI ≥ {minimum}, blocking from {severity}", { minimum: fmt(g.policy.min_score, 0), severity: tokenLabel(t, g.policy.block_severity) })}
        </span>
      </div>
      {g.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm">
          {g.reasons.map((r) => (
            <li key={String(r.code)}>{reasonText(t, r, g.policy)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Per-project acceptance thresholds; they belong in the BEP, so they are editable and printed in the report. */
export function GatePolicyPanel({ projectId }: { projectId: number }) {
  const { t } = useT();
  const stored = useGatePolicy(projectId).data;
  const save = useSetGatePolicy(projectId);
  const [draft, setDraft] = useState<GatePolicy | null>(null);
  const p = draft ?? stored;
  if (!p) return null;
  const set = (patch: Partial<GatePolicy>) => setDraft({ ...p, ...patch });
  return (
    <Panel title={t("Acceptance gate")}>
      <form
        className="flex flex-wrap items-end gap-4 px-3 py-2 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(p, { onSuccess: () => setDraft(null) });
        }}
      >
        <label className="flex flex-col gap-1 text-xs text-muted">
          {t("Minimum MHI")}
          <input
            type="number"
            min={0}
            max={100}
            step={1}
            required
            className={`${input} w-24 text-fg`}
            value={p.min_score}
            onChange={(e) => set({ min_score: e.target.valueAsNumber })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">
          {t("Reject on open findings from severity")}
          <select className={`${input} text-fg`} value={p.block_severity} onChange={(e) => set({ block_severity: e.target.value as GatePolicy["block_severity"] })}>
            {BLOCK_SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {tokenLabel(t, s)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex h-8 items-center gap-2">
          <input type="checkbox" checked={p.require_ids} onChange={(e) => set({ require_ids: e.target.checked })} />
          {t("Require a client requirements file (IDS)")}
        </label>
        <button className={btn} disabled={draft == null || save.isPending}>
          {t("Save")}
        </button>
        {save.isError && <span className="text-xs text-sev-critical">{t("Could not save the gate policy.")}</span>}
      </form>
    </Panel>
  );
}
