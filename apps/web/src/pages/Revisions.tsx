import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { GitCompareArrows, LoaderCircle } from "lucide-react";
import { useEffect } from "react";
import { useParams, useSearchParams } from "react-router";
import { api, postJson, type Audit, type Revision } from "../api/client";
import { useComparisons, useJob, useRevision, useRevisions } from "../api/queries";
import { btnPrimary, Empty, fmt, input, Panel, Q } from "../ui";
import { ComparisonView } from "./ComparisonView";

/** Revision Intelligence: pick two revisions of a model and read what changed between them. */
export function Revisions() {
  const modelId = Number(useParams().modelId);
  const revisions = useRevisions(modelId);
  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <h1 className="text-lg font-semibold">Revision Intelligence</h1>
      <Q q={revisions} empty={(d) => d.length < 2 && "Upload at least two revisions of this model to compare them."}>
        {(revs: Revision[]) => <Picker revs={revs} />}
      </Q>
    </div>
  );
}

function Picker({ revs }: { revs: Revision[] }) {
  const [params, setParams] = useSearchParams();
  const head = Number(params.get("head")) || revs.at(-1)!.id;
  const base = Number(params.get("base")) || revs.at(-2)!.id;
  const seq = (id: number) => revs.find((r) => r.id === id)?.seq ?? 0;
  const pick = (key: "base" | "head", id: string) => setParams({ base: String(base), head: String(head), [key]: id });
  const select = (key: "base" | "head", value: number, label: string) => (
    <label className="flex items-center gap-2 text-sm">
      {label}
      <select className={input} value={value} onChange={(e) => pick(key, e.target.value)}>
        {revs.map((r) => (
          <option key={r.id} value={r.id}>
            r{r.seq}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <>
      <Panel title="Revisions">
        <div className="flex flex-wrap items-center gap-6">
          <Sparkline revs={revs} marks={[base, head]} />
          {select("base", base, "Base (older)")}
          {select("head", head, "Head (newer)")}
        </div>
      </Panel>
      {seq(base) >= seq(head) ? (
        <Empty>Pick a base revision older than the head revision.</Empty>
      ) : (
        <Comparing base={base} head={head} seqs={[seq(base), seq(head)]} />
      )}
    </>
  );
}

const SPARK_W = 44; // px per revision
const SPARK_H = 40;

function Sparkline({ revs, marks }: { revs: Revision[]; marks: number[] }) {
  const audits = useQueries({
    queries: revs.map((r) => ({ queryKey: ["audits", r.id], queryFn: () => api<Audit[]>(`/revisions/${r.id}/audits`) })),
  });
  const scores = audits.map((a) => a.data?.[0]?.score ?? null);
  const y = (s: number) => SPARK_H - 4 - (s / 100) * (SPARK_H - 8);
  const pts = scores.map((s, i) => (s == null ? null : `${i * SPARK_W + 8},${y(s)}`)).filter(Boolean);
  const label = revs.map((r, i) => `r${r.seq} ${fmt(scores[i])}`).join(", ");
  return (
    <figure className="flex items-end gap-2">
      <svg width={(revs.length - 1) * SPARK_W + 16} height={SPARK_H + 14} role="img" aria-label={`Health index by revision: ${label}`}>
        <polyline points={pts.join(" ")} fill="none" className="stroke-accent" strokeWidth={1.5} />
        {revs.map((r, i) => (
          <g key={r.id}>
            {scores[i] != null && (
              <circle cx={i * SPARK_W + 8} cy={y(scores[i]!)} r={marks.includes(r.id) ? 4 : 2.5} className={marks.includes(r.id) ? "fill-accent" : "fill-muted"} />
            )}
            <text x={i * SPARK_W + 8} y={SPARK_H + 12} textAnchor="middle" className="fill-muted text-[10px]">
              r{r.seq}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="text-xs text-muted">MHI</figcaption>
    </figure>
  );
}

function Comparing({ base, head, seqs }: { base: number; head: number; seqs: [number, number] }) {
  const comparisons = useComparisons(head);
  const headRev = useRevision(head);
  const found = comparisons.data?.filter((c) => c.base_revision_id === base && c.head_revision_id === head).at(-1);
  if (comparisons.isPending || headRev.isPending) return <Empty>Loading comparison…</Empty>;
  if (!found) return <RequestComparison base={base} head={head} seqs={seqs} />;
  return <ComparisonView c={found} head={headRev.data!} seqs={seqs} />;
}

function RequestComparison({ base, head, seqs }: { base: number; head: number; seqs: [number, number] }) {
  const qc = useQueryClient();
  const m = useMutation({ mutationFn: () => postJson<{ job_id: number }>("/comparisons", { base_revision_id: base, head_revision_id: head }) });
  const job = useJob(m.data?.job_id).data;
  useEffect(() => {
    if (job?.status === "done") qc.invalidateQueries({ queryKey: ["comparisons", head] });
  }, [job?.status, head, qc]);
  const busy = m.isPending || (m.isSuccess && job?.status !== "done" && job?.status !== "failed");
  return (
    <Panel>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span>
          r{seqs[0]} and r{seqs[1]} have not been compared yet.
        </span>
        <button className={btnPrimary} disabled={busy} onClick={() => m.mutate()}>
          {busy ? <LoaderCircle size={14} className="animate-spin" aria-hidden /> : <GitCompareArrows size={14} aria-hidden />}
          Compare r{seqs[0]} → r{seqs[1]}
        </button>
        {(m.error || job?.status === "failed") && (
          <span role="alert" className="text-sev-critical">
            Comparison failed: {m.error?.message ?? job?.error_message ?? "unknown error"}
          </span>
        )}
      </div>
    </Panel>
  );
}
