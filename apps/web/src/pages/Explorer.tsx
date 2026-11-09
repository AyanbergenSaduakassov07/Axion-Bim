import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import type { Element, Finding, SpatialTree, TreeElement } from "../api/client";
import { useElement, useFindings, useRevision, useTree } from "../api/queries";
import { btn, Empty, fmt, Panel, Q, Severity, Status } from "../ui";
import { useFocus, Viewport, type Viewer } from "../viewer/Viewport";

export function Explorer() {
  const revisionId = Number(useParams().revisionId);
  const rev = useRevision(revisionId);
  const tree = useTree(revisionId);
  const findings = useFindings(rev.data?.latest_audit_id);
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const initial = useSearchParams()[0].get("focus"); // copilot citation deep link
  const [selected, setSelected] = useState<string | null>(initial);
  const [target, setTarget] = useState<string | null>(initial); // tree picks fly the camera; 3D clicks only select
  const focus = useFocus(viewer, target);

  useEffect(() => viewer?.onSelect(setSelected), [viewer]);
  const pick = (gid: string) => {
    setSelected(gid);
    setTarget(gid);
  };

  return (
    <div className="flex h-[calc(100dvh-4.5rem)] flex-col gap-3">
      <div className="flex items-baseline gap-3">
        <h1 className="text-lg font-semibold">Model Explorer</h1>
        {rev.data && <span className="text-sm text-muted">r{rev.data.seq} · {String(rev.data.metadata.project_name ?? "")}</span>}
        <Link className={`${btn} ml-auto`} to={`/revisions/${revisionId}/quality`}>
          Quality Center
        </Link>
      </div>
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[280px_1fr_340px]">
        <section aria-label="Spatial structure" className="flex min-h-0 flex-col overflow-auto rounded border border-line bg-panel">
          <Q q={tree} rows={10}>
            {(t: SpatialTree) => <TreePanel tree={t} selected={selected} onPick={pick} viewer={viewer} />}
          </Q>
        </section>
        {rev.data ? (
          <Viewport
            className="min-h-80"
            fileUrl={`/api/v1/revisions/${revisionId}/file`}
            sha={rev.data.file_sha256}
            onViewer={setViewer}
            overlay={
              focus === "no_geometry" && (
                <div role="status" className="absolute inset-x-2 bottom-2 rounded border border-line bg-raised px-2 py-1 text-xs">
                  Element has no renderable geometry.
                </div>
              )
            }
          />
        ) : (
          <div className="rounded border border-line bg-panel" />
        )}
        <aside className="min-h-0 overflow-auto rounded border border-line bg-panel">
          {selected ? (
            <ElementPanel revisionId={revisionId} globalId={selected} findings={findings.data ?? []} />
          ) : (
            <Empty>Select an element in the tree or the 3D view.</Empty>
          )}
        </aside>
      </div>
    </div>
  );
}

// shortcut: tree is not virtualized; fine for thousands of elements, virtualize if large models stutter.
function TreePanel({ tree, selected, onPick, viewer }: { tree: SpatialTree; selected: string | null; onPick: (g: string) => void; viewer: Viewer | null }) {
  const { roots, children, byContainer, classes } = useMemo(() => index(tree), [tree]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const toggle = async (cls: string) => {
    const next = new Set(hidden);
    if (next.has(cls)) next.delete(cls);
    else next.add(cls);
    setHidden(next);
    await viewer?.setClassVisibility(cls, !next.has(cls));
  };

  const node = (gid: string, depth: number): ReactNode => {
    const n = tree.nodes.find((x) => x.global_id === gid)!;
    const els = (byContainer.get(gid) ?? []).filter((e) => !hidden.has(e.ifc_class));
    return (
      <details key={gid} open={depth < 4} className="pl-2">
        <summary className="cursor-pointer py-0.5 text-sm">
          <span className="text-muted">{n.ifc_class.replace("Ifc", "")}</span> {n.name ?? "—"}
          {n.elevation_m != null && <span className="text-xs text-muted"> · {fmt(n.elevation_m, 2)} m</span>}
        </summary>
        {(children.get(gid) ?? []).map((c) => node(c, depth + 1))}
        <ul className="pl-3">
          {els.map((e) => (
            <li key={`${e.global_id}-${e.step_id}`}>
              <button
                className={`w-full truncate rounded px-1 text-left text-sm hover:bg-raised ${e.global_id === selected ? "bg-raised text-accent" : ""}`}
                onClick={() => onPick(e.global_id)}
                aria-current={e.global_id === selected || undefined}
              >
                {e.name ?? "—"} <span className="text-xs text-muted">{e.ifc_class}{e.has_geometry ? "" : " · no geometry"}</span>
              </button>
            </li>
          ))}
        </ul>
      </details>
    );
  };

  return (
    <div className="space-y-2 p-2">
      <fieldset className="border-b border-line pb-2">
        <legend className="mb-1 text-xs text-muted">Classes</legend>
        {classes.map(([cls, n]) => (
          <label key={cls} className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={!hidden.has(cls)} onChange={() => toggle(cls)} disabled={!viewer} />
            {cls} <span className="text-xs text-muted">{n}</span>
          </label>
        ))}
      </fieldset>
      {roots.map((r) => node(r, 0))}
    </div>
  );
}

function index(tree: SpatialTree) {
  const children = new Map<string, string[]>();
  const roots: string[] = [];
  for (const n of tree.nodes) {
    if (n.parent_global_id) children.set(n.parent_global_id, [...(children.get(n.parent_global_id) ?? []), n.global_id]);
    else roots.push(n.global_id);
  }
  const byContainer = new Map<string, TreeElement[]>();
  const counts = new Map<string, number>();
  for (const e of tree.elements) {
    const key = e.container_global_id ?? "";
    byContainer.set(key, [...(byContainer.get(key) ?? []), e]);
    counts.set(e.ifc_class, (counts.get(e.ifc_class) ?? 0) + 1);
  }
  return { roots, children, byContainer, classes: [...counts].sort((a, b) => a[0].localeCompare(b[0])) };
}

function ElementPanel({ revisionId, globalId, findings }: { revisionId: number; globalId: string; findings: Finding[] }) {
  const q = useElement(revisionId, globalId);
  const mine = findings.filter((f) => f.global_id === globalId);
  return (
    <Q q={q} rows={6}>
      {(el: Element) => (
        <div className="space-y-3 p-3 text-sm">
          <div>
            <div className="font-semibold">{el.name ?? "—"}</div>
            <div className="text-xs text-muted">{el.ifc_class}{el.predefined_type ? ` · ${el.predefined_type}` : ""}</div>
            <div className="font-mono text-xs text-muted">{el.global_id}</div>
          </div>
          <Panel title={`Findings (${mine.length})`}>
            {mine.length === 0 ? (
              <p className="text-muted">No findings for this element in the latest audit.</p>
            ) : (
              <ul className="space-y-1">
                {mine.map((f) => (
                  <li key={f.identity_key} className="flex flex-wrap items-center gap-2">
                    <Severity value={f.severity} /> <Status value={f.status} /> <span className="text-xs">{f.rule_id}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Quantities">
            <Rows rows={el.quantities.map((x) => [`${x.qto}.${x.name}`, `${fmt(x.value, 3)} ${x.unit ?? "(unit not declared)"} · ${x.method}`])} />
          </Panel>
          <Panel title="Properties">
            {el.properties.length === 0 && <p className="text-muted">None declared.</p>}
            {[...byPset(el.properties)].map(([pset, props]) => (
              <div key={pset} className="mb-2 last:mb-0">
                <div className="mb-0.5 truncate text-xs font-medium" title={pset}>{pset}</div>
                <Rows rows={props.map((p) => [p.name, value(p.value)])} />
              </div>
            ))}
          </Panel>
          <Panel title="Materials">
            <Rows rows={el.materials.map((m) => [m.name, m.kind])} />
          </Panel>
        </div>
      )}
    </Q>
  );
}

function byPset<T extends { pset: string }>(props: T[]): Map<string, T[]> {
  const m = new Map<string, T[]>();
  for (const p of props) m.set(p.pset, [...(m.get(p.pset) ?? []), p]);
  return m;
}

const value = (v: unknown) =>
  typeof v === "number" ? v.toLocaleString("en-US", { maximumFractionDigits: 3 }) : String(v ?? "—");

function Rows({ rows }: { rows: [string, string][] }) {
  if (rows.length === 0) return <p className="text-muted">None declared.</p>;
  return (
    <dl className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-xs">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="truncate text-muted" title={k}>{k}</dt>
          <dd className="break-words text-right">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
