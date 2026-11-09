import type { UseQueryResult } from "@tanstack/react-query";
import {
  Bug,
  Check,
  CircleAlert,
  CircleDashed,
  CircleX,
  Info,
  OctagonAlert,
  RotateCw,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link, Outlet } from "react-router";

export const SEVERITIES = ["critical", "high", "medium", "low", "info"] as const;

const SEV_ICON: Record<string, LucideIcon> = {
  critical: OctagonAlert,
  high: TriangleAlert,
  medium: CircleAlert,
  low: Info,
  info: Info,
};
const SEV_TEXT: Record<string, string> = {
  critical: "text-sev-critical",
  high: "text-sev-high",
  medium: "text-sev-medium",
  low: "text-sev-low",
  info: "text-sev-info",
};
const STATUS: Record<string, [LucideIcon, string]> = {
  pass: [Check, "text-ok"],
  fail: [CircleX, "text-sev-critical"],
  warning: [TriangleAlert, "text-sev-medium"],
  error: [Bug, "text-sev-high"],
  not_evaluated: [CircleDashed, "text-ne"],
  not_applicable: [CircleDashed, "text-muted"],
};

export function Severity({ value }: { value: string }) {
  const Icon = SEV_ICON[value] ?? Info;
  return (
    <span className={`inline-flex items-center gap-1 ${SEV_TEXT[value] ?? ""}`}>
      <Icon size={14} aria-hidden />
      {value}
    </span>
  );
}

export function Status({ value }: { value: string }) {
  const [Icon, cls] = STATUS[value] ?? [CircleDashed, "text-muted"];
  return (
    <span className={`inline-flex items-center gap-1 ${cls}`}>
      <Icon size={14} aria-hidden />
      {value.replace("_", " ")}
    </span>
  );
}

/** Resolved token colour (hex) for canvas/WebGL consumers that cannot read CSS variables. */
export const tokenColor = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim();

export const fmt = (n: number | null | undefined, digits = 1) => (n == null ? "—" : n.toFixed(digits));
export const date = (iso: string) => iso.replace("T", " ").slice(0, 16);
export const bytes = (n: number) => (n < 1e6 ? `${(n / 1e3).toFixed(1)} kB` : `${(n / 1e6).toFixed(1)} MB`);

export function Panel({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded border border-line bg-panel">
      {title && (
        <header className="flex items-center justify-between border-b border-line px-3 py-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h2>
          {actions}
        </header>
      )}
      <div className="p-3">{children}</div>
    </section>
  );
}

export const btn =
  "inline-flex h-8 items-center gap-1.5 rounded border border-line bg-raised px-3 text-sm hover:border-accent disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer";
export const btnPrimary =
  "inline-flex h-8 items-center gap-1.5 rounded bg-accent px-3 text-sm font-medium text-accent-fg hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer";
export const input = "h-8 rounded border border-line bg-bg px-2 text-sm placeholder:text-muted";

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading" className="space-y-2">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-raised" />
      ))}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-2 text-sm">
      <CircleX size={16} className="mt-0.5 shrink-0 text-sev-critical" aria-hidden />
      <div className="space-y-2">
        <p>{error.message}</p>
        {retry && (
          <button className={btn} onClick={retry}>
            <RotateCw size={14} aria-hidden /> Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-4 text-center text-sm text-muted">{children}</p>;
}

/** Loading / error / empty handling shared by every query. */
export function Q<T>({
  q,
  empty,
  rows,
  children,
}: {
  q: UseQueryResult<T>;
  empty?: (d: T) => ReactNode | false;
  rows?: number;
  children: (d: T) => ReactNode;
}) {
  if (q.isPending) return <Skeleton rows={rows} />;
  if (q.isError) return <ErrorState error={q.error} retry={() => q.refetch()} />;
  const e = empty?.(q.data);
  return e ? <Empty>{e}</Empty> : <>{children(q.data)}</>;
}

export function Shell() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-2">
        Skip to content
      </a>
      <header className="flex h-10 items-center gap-4 border-b border-line bg-panel px-4">
        <Link to="/" className="text-sm font-semibold tracking-wide">
          AXIOM <span className="text-muted">BIM</span>
        </Link>
        <nav className="text-sm text-muted">
          <Link to="/" className="hover:text-fg">
            Projects
          </Link>
        </nav>
      </header>
      <main id="main" className="flex-1 p-4">
        <Outlet />
      </main>
    </div>
  );
}
