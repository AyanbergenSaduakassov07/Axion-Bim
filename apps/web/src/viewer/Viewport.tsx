import { LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { createViewer, type FocusResult, type Viewer } from "./viewer";
import { handleViewKey, ViewControls } from "./ViewControls";

export type { FocusResult, Viewer } from "./viewer";

type State = { kind: "loading"; progress: number } | { kind: "ready" } | { kind: "error"; message: string };

/** Mounts a viewer, loads one revision file, and hands the ready viewer to the parent. */
export function Viewport({
  fileUrl,
  sha,
  onViewer,
  className = "",
  overlay,
}: {
  fileUrl: string;
  sha: string;
  onViewer: (v: Viewer | null) => void;
  className?: string;
  overlay?: ReactNode;
}) {
  const el = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<State>({ kind: "loading", progress: 0 });
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const cb = useRef(onViewer);
  cb.current = onViewer;

  useEffect(() => {
    const v = createViewer(el.current!);
    let live = true;
    setState({ kind: "loading", progress: 0 });
    v.load(fileUrl, sha, (p) => live && setState({ kind: "loading", progress: p }))
      .then(() => {
        if (!live) return;
        setState({ kind: "ready" });
        setViewer(v);
        cb.current(v);
      })
      .catch((e: Error) => {
        if (!live && String(e?.message ?? e).includes("Fragments: Model not found")) {
          return;
        }
        if (live) setState({ kind: "error", message: e.message });
      });
    return () => {
      live = false;
      setViewer(null);
      cb.current(null);
      v.dispose();
    };
  }, [fileUrl, sha]);

  return (
    <div className={`relative overflow-hidden rounded border border-line bg-panel ${className}`}>
      <div
        ref={el}
        className="absolute inset-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        aria-label="3D model viewer. Arrow keys orbit, Shift+arrows pan, plus and minus zoom, F fits the model."
        role="application"
        tabIndex={0}
        onKeyDown={(e) => viewer && handleViewKey(viewer, e) && e.preventDefault()}
      />
      {state.kind === "loading" && (
        <div className="absolute inset-0 flex items-center justify-center gap-2 text-sm text-muted" aria-live="polite">
          <LoaderCircle size={16} className="animate-spin text-accent" aria-hidden />
          Preparing 3D model…{state.progress > 0 && ` ${Math.round(Math.min(state.progress, 1) * 100)}%`}
        </div>
      )}
      {state.kind === "error" && (
        <div role="alert" className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-sev-critical">
          {state.message}
        </div>
      )}
      {state.kind === "ready" && overlay}
      {viewer && <ViewControls viewer={viewer} />}
    </div>
  );
}

/** Focus `globalId` whenever it or the viewer changes (a pick made while loading applies once ready). */
export function useFocus(viewer: Viewer | null, globalId: string | null | undefined) {
  const [result, setResult] = useState<FocusResult | null>(null);
  useEffect(() => {
    setResult(null);
    if (!viewer || !globalId) return;
    let live = true;
    viewer.focus(globalId)
      .then((r) => live && setResult(r))
      .catch((e: Error) => {
        if (live) console.warn("[viewer] focus failed", e); // after dispose the model is gone: expected
      });
    return () => {
      live = false;
    };
  }, [viewer, globalId]);
  return result;
}

