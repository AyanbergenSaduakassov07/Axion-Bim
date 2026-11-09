const MIN_STEP = 0.05; // points; smaller dimension moves are listed as unchanged

export type Step = { label: string; from: number; to: number; kind: "total" | "up" | "down" };

export function buildSteps(base: number, head: number, dims: Record<string, number>, seqs: [number, number]) {
  const steps: Step[] = [{ label: `r${seqs[0]}`, from: 0, to: base, kind: "total" }];
  let at = base;
  const add = (label: string, d: number) => {
    steps.push({ label, from: at, to: at + d, kind: d > 0 ? "up" : "down" });
    at += d;
  };
  const moved = Object.entries(dims).filter(([, d]) => Math.abs(d) >= MIN_STEP);
  moved.sort((x, y) => Math.abs(y[1]) - Math.abs(x[1])).forEach(([k, d]) => add(k.replace(/_/g, " "), d));
  // contributions need not sum exactly to the score delta (coverage re-weighting, rounding)
  if (Math.abs(head - at) >= MIN_STEP) add("other (re-weighting)", head - at);
  steps.push({ label: `r${seqs[1]}`, from: 0, to: head, kind: "total" });
  return { steps, unchanged: Object.keys(dims).length - moved.length };
}
