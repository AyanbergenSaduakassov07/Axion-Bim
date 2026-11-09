import type { ComparisonSummary } from "../api/client";
import { fmt } from "../ui";
import { buildSteps } from "./waterfall-steps";

const AXIS_PAD = 5;

/** Base score → one floating bar per dimension's contribution change → head score. */
export function Waterfall({ mhi, seqs }: { mhi: ComparisonSummary["mhi"]; seqs: [number, number] }) {
  if (mhi.base == null || mhi.head == null) {
    return <p className="text-sm text-muted">Score withheld in at least one revision (blocking findings), so there is no score change to break down.</p>;
  }
  const { steps, unchanged } = buildSteps(mhi.base, mhi.head, mhi.dimensions, seqs);
  const values = steps.flatMap((s) => [s.from, s.to]);
  // shortcut: the axis starts near the lowest value so sub-point moves stay visible; labelled below
  const lo = Math.max(0, Math.floor((Math.min(...values) - AXIS_PAD) / AXIS_PAD) * AXIS_PAD);
  const pct = (v: number) => ((v - lo) / (100 - lo)) * 100;
  return (
    <figure className="space-y-1 text-sm">
      {steps.map((s) => {
        const [a, b] = [Math.max(lo, Math.min(s.from, s.to)), Math.max(s.from, s.to)];
        const color = s.kind === "total" ? "bg-muted" : s.kind === "up" ? "bg-ok" : "bg-sev-high";
        return (
          <div key={s.label} className="grid grid-cols-[150px_1fr_56px] items-center gap-2">
            <span className="truncate text-xs" title={s.label}>{s.label}</span>
            <div className="relative h-4 rounded-sm bg-raised">
              <div className={`absolute inset-y-0 rounded-sm ${color}`} style={{ left: `${pct(a)}%`, width: `max(2px, ${pct(b) - pct(a)}%)` }} />
            </div>
            <span className="text-right text-xs tabular-nums">{s.kind === "total" ? fmt(s.to) : `${s.to > s.from ? "+" : "−"}${fmt(Math.abs(s.to - s.from))}`}</span>
          </div>
        );
      })}
      <figcaption className="text-xs text-muted">
        Axis {lo}–100 MHI points.{unchanged > 0 && ` ${unchanged} dimension${unchanged > 1 ? "s" : ""} unchanged.`}
      </figcaption>
    </figure>
  );
}
