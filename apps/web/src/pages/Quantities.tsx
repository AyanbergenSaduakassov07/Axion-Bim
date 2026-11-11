import { useParams, useSearchParams } from "react-router";
import type { Quantities as Q_, QuantityDelta } from "../api/client";
import { decisionLabel } from "./Gate";
import { useQuantities, useRevision, useRevisions } from "../api/queries";
import { btn, fmt, input, Panel, Q, RevisionNav } from "../ui";
import { useT } from "../i18n";

const GROUPS = ["class", "storey", "material", "classification"] as const;
const keyOf = (r: { group: string; qto: string; quantity: string }) => `${r.group}|${r.qto}|${r.quantity}`;

/** Qto totals per group, with the change against an earlier revision (default: the previous one). */
export function Quantities() {
  const revisionId = Number(useParams().revisionId);
  const [params, setParams] = useSearchParams();
  const by = params.get("by") ?? "class";
  const rev = useRevision(revisionId).data;
  const revs = useRevisions(rev?.model_id ?? 0).data;
  const earlier = revs?.filter((r) => rev && r.seq < rev.seq) ?? [];
  const prev = earlier.find((r) => String(r.id) === params.get("against")) ?? earlier.at(-1);
  const set = (key: string, value: string) => setParams({ ...Object.fromEntries(params), [key]: value });
  const q = useQuantities(revisionId, by, prev?.id);
  const { t } = useT();
  const groupBy = (
    <label className="flex items-center gap-2 text-sm">
      {t("Group by")}
      <select className={input} value={by} onChange={(e) => set("by", e.target.value)}>
        {GROUPS.map((g) => (
          <option key={g} value={g}>
            {t(g)}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <RevisionNav
        revisionId={revisionId}
        title={t("Quantities")}
        actions={
          <div className="flex items-center gap-3">
            {groupBy}
            {earlier.length > 1 && (
              <label className="flex items-center gap-2 text-sm">
                {t("Compare with")}
                <select className={input} value={prev?.id} onChange={(e) => set("against", e.target.value)}>
                  {earlier.map((r) => (
                    <option key={r.id} value={r.id}>
                      r{r.seq}
                      {r.decision ? ` · ${decisionLabel(t, r.decision)}` : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <a className={btn} href={`/api/v1/revisions/${revisionId}/quantities?by=${by}&format=csv${prev ? `&against=${prev.id}` : ""}`} download>
              {t("Export CSV (Excel)")}
            </a>
          </div>
        }
      />
      <Panel>
        <Q q={q} empty={(d) => d.rows.length === 0 && t("No quantity sets (Qto_*) in this revision.")}>
          {(d: Q_) => <QuantityTable data={d} prevSeq={prev?.seq} />}
        </Q>
      </Panel>
      <p className="text-xs text-muted">
        {t(
          "Method qto: values declared in the model's Qto_* property sets. Method geometry: volume measured from the element's 3D shape (shown after a geometry audit). Missing: elements of the group without that quantity.",
        )}
      </p>
    </div>
  );
}

function QuantityTable({ data, prevSeq }: { data: Q_; prevSeq?: number }) {
  const deltas = new Map<string, QuantityDelta>(data.delta.map((d) => [keyOf(d), d]));
  const { t } = useT();
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs text-muted">
        <tr>
          <th className="py-1">{t("Group")}</th>
          <th>{t("Quantity")}</th>
          <th>{t("Method")}</th>
          <th className="text-right">{t("Total")}</th>
          <th>{t("Unit")}</th>
          <th className="text-right">{t("Elements")}</th>
          <th className="text-right">{t("Missing")}</th>
          {prevSeq != null && <th className="text-right">{t("Δ vs r{n}", { n: prevSeq })}</th>}
        </tr>
      </thead>
      <tbody className="tabular-nums">
        {data.rows.map((r) => {
          const d = deltas.get(keyOf(r));
          const change = d && d.old != null && d.new != null ? d.new - d.old : null;
          return (
            <tr key={keyOf(r)} className="border-t border-line">
              <td className="py-1">{r.group}</td>
              <td>
                {r.qto}.{r.quantity}
              </td>
              <td>{t(r.method)}</td>
              <td className="text-right">{fmt(r.total, 2)}</td>
              <td>{r.unit ?? "—"}</td>
              <td className="text-right">{r.count}</td>
              <td className="text-right" title={r.missing.join(", ")}>
                {r.missing.length}
              </td>
              {prevSeq != null && (
                <td className="text-right">{d == null ? "—" : change == null ? (d.old == null ? t("new") : t("removed")) : `${change >= 0 ? "+" : "−"}${fmt(Math.abs(change), 2)}`}</td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
