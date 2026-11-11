import { useState } from "react";
import type { Coordination } from "../api/client";
import { useCoordination } from "../api/queries";
import { useT, type T } from "../i18n";
import { input, Panel, Status } from "../ui";
import { decisionLabel, STAGES, stageLabel, TONE } from "./Gate";

function checkLabel(t: T, c: Coordination["checks"][number]["check"]): string {
  if (c === "length_unit") return t("Length unit");
  if (c === "georeferencing") return t("Georeferencing");
  return t("Storey levels");
}

/** Display rounding only: drops float noise like 2.70000000000008 (the backend keeps full values). */
const round = (x: unknown, digits: number) => (typeof x === "number" ? String(Number(x.toFixed(digits))) : String(x));

function value(v: unknown): string {
  if (v == null) return "—";
  if (Array.isArray(v)) return v.map((e) => `${round(e, 3)} m`).join(", ") || "—"; // storey levels to the mm
  if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${k} ${round(x, 6)}`).join(", "); // ~0.1 m
  return String(v);
}

/** Project-level decision over every model's latest delivery and cross-model consistency (D-39). */
export function CoordinationPanel({ projectId }: { projectId: number }) {
  const { t } = useT();
  const [stage, setStage] = useState("");
  const d = useCoordination(projectId, stage).data;
  if (!d || d.models.length === 0) return null;
  return (
    <Panel title={t("Project coordination")}>
      <div className="space-y-3 px-3 py-2 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded border px-2 py-0.5 font-semibold ${TONE[d.decision]}`} data-testid="project-decision">
            {decisionLabel(t, d.decision)}
          </span>
          {d.models.map((m) => (
            <span key={m.model_id} className="text-muted">
              {m.name} {m.seq != null ? `r${m.seq}` : ""}: {m.decision ? decisionLabel(t, m.decision) : t("no delivery")}
            </span>
          ))}
          <label className="ml-auto flex items-center gap-1 text-xs text-muted">
            {t("Stage")}
            <select className={`${input} text-fg`} value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="">{t("Latest delivery")}</option>
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {stageLabel(t, s)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <table className="w-full text-left">
          <tbody>
            {d.checks.map((c) => (
              <tr key={c.check} className="border-t border-line">
                <td className="py-1 pr-3">{checkLabel(t, c.check)}</td>
                <td className="py-1 pr-3">
                  <Status value={c.status} />
                </td>
                <td className="py-1 text-muted">
                  {Object.entries(c.actual).map(([model, v]) => (
                    <div key={model}>
                      {model}: {value(v)}
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-muted">
          {t("Latest revision of each model. Storey levels lists only the levels that the other models do not have (10 mm tolerance).")}
        </p>
      </div>
    </Panel>
  );
}
