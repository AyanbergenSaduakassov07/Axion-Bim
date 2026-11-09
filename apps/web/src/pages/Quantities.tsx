import { useParams, useSearchParams } from "react-router";
import type { Quantities as Q_, QuantityDelta } from "../api/client";
import { useQuantities, useRevision, useRevisions } from "../api/queries";
import { fmt, input, Panel, Q } from "../ui";

const GROUPS = ["class", "storey", "material", "classification"] as const;
const keyOf = (r: { group: string; qto: string; quantity: string }) => `${r.group}|${r.qto}|${r.quantity}`;

/** Qto totals per group, with the change against the previous revision of the same model. */
export function Quantities() {
  const revisionId = Number(useParams().revisionId);
  const [params, setParams] = useSearchParams();
  const by = params.get("by") ?? "class";
  const rev = useRevision(revisionId).data;
  const revs = useRevisions(rev?.model_id ?? 0).data;
  const prev = revs?.filter((r) => rev && r.seq < rev.seq).at(-1);
  const q = useQuantities(revisionId, by, prev?.id);
  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">Quantities{rev && ` · r${rev.seq}`}</h1>
        <label className="flex items-center gap-2 text-sm">
          Group by
          <select className={input} value={by} onChange={(e) => setParams({ by: e.target.value })}>
            {GROUPS.map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </label>
      </div>
      <Panel>
        <Q q={q} empty={(d) => d.rows.length === 0 && "No quantity sets (Qto_*) in this revision."}>
          {(d: Q_) => <QuantityTable data={d} prevSeq={prev?.seq} />}
        </Q>
      </Panel>
      <p className="text-xs text-muted">
        Method qto: values read from the model's Qto_* property sets, not measured from geometry. Missing lists elements of the
        group without that quantity.
      </p>
    </div>
  );
}

function QuantityTable({ data, prevSeq }: { data: Q_; prevSeq?: number }) {
  const deltas = new Map<string, QuantityDelta>(data.delta.map((d) => [keyOf(d), d]));
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs text-muted">
        <tr>
          <th className="py-1">Group</th>
          <th>Quantity</th>
          <th>Method</th>
          <th className="text-right">Total</th>
          <th>Unit</th>
          <th className="text-right">Elements</th>
          <th className="text-right">Missing</th>
          {prevSeq != null && <th className="text-right">Δ vs r{prevSeq}</th>}
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
              <td>{r.method}</td>
              <td className="text-right">{fmt(r.total, 2)}</td>
              <td>{r.unit ?? "—"}</td>
              <td className="text-right">{r.count}</td>
              <td className="text-right" title={r.missing.join(", ")}>
                {r.missing.length}
              </td>
              {prevSeq != null && (
                <td className="text-right">{d == null ? "—" : change == null ? (d.old == null ? "new" : "removed") : `${change >= 0 ? "+" : "−"}${fmt(Math.abs(change), 2)}`}</td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
