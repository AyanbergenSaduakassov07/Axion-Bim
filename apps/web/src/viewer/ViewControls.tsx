import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ChevronDown,
  ChevronUp,
  Maximize,
  RotateCcw,
  RotateCw,
  ZoomIn,
  ZoomOut,
  type LucideIcon,
} from "lucide-react";
import type { Viewer } from "./viewer";

const ORBIT_STEP = 15; // degrees per click
const TILT_STEP = 10;
const ZOOM_STEP = 1.25;
const PAN_STEP = 0.15; // fraction of the camera distance

type Action = { label: string; key: string; icon: LucideIcon; run: (v: Viewer) => Promise<void> };

const ZOOM: Action[] = [
  { label: "Zoom in", key: "+", icon: ZoomIn, run: (v) => v.zoom(ZOOM_STEP) },
  { label: "Zoom out", key: "-", icon: ZoomOut, run: (v) => v.zoom(1 / ZOOM_STEP) },
  { label: "Fit model", key: "F", icon: Maximize, run: (v) => v.fitAll() },
];
const ORBIT: Action[] = [
  { label: "Tilt up", key: "↑", icon: ChevronUp, run: (v) => v.orbit(0, -TILT_STEP) },
  { label: "Rotate left", key: "←", icon: RotateCcw, run: (v) => v.orbit(ORBIT_STEP, 0) },
  { label: "Rotate right", key: "→", icon: RotateCw, run: (v) => v.orbit(-ORBIT_STEP, 0) },
  { label: "Tilt down", key: "↓", icon: ChevronDown, run: (v) => v.orbit(0, TILT_STEP) },
];
const PAN: Action[] = [
  { label: "Pan up", key: "Shift+↑", icon: ArrowUp, run: (v) => v.pan(0, PAN_STEP) },
  { label: "Pan left", key: "Shift+←", icon: ArrowLeft, run: (v) => v.pan(-PAN_STEP, 0) },
  { label: "Pan right", key: "Shift+→", icon: ArrowRight, run: (v) => v.pan(PAN_STEP, 0) },
  { label: "Pan down", key: "Shift+↓", icon: ArrowDown, run: (v) => v.pan(0, -PAN_STEP) },
];

const KEYS: Record<string, Action> = {
  "+": ZOOM[0], "=": ZOOM[0], "-": ZOOM[1], f: ZOOM[2], F: ZOOM[2],
  ArrowUp: ORBIT[0], ArrowLeft: ORBIT[1], ArrowRight: ORBIT[2], ArrowDown: ORBIT[3],
  "Shift+ArrowUp": PAN[0], "Shift+ArrowLeft": PAN[1], "Shift+ArrowRight": PAN[2], "Shift+ArrowDown": PAN[3],
}; // prettier-ignore

/** Keyboard navigation for the focused viewport; returns true when the key was handled. */
export function handleViewKey(v: Viewer, e: { key: string; shiftKey: boolean }): boolean {
  const a = KEYS[e.shiftKey && e.key.startsWith("Arrow") ? `Shift+${e.key}` : e.key];
  if (!a) return false;
  a.run(v).catch((err: Error) => console.warn("[viewer] navigation failed", err));
  return true;
}

function Button({ a, v }: { a: Action; v: Viewer }) {
  const Icon = a.icon;
  return (
    <button
      type="button"
      title={`${a.label} (${a.key})`}
      aria-label={a.label}
      onClick={() => a.run(v).catch((err: Error) => console.warn("[viewer] navigation failed", err))}
      className="flex h-8 w-8 items-center justify-center rounded text-muted hover:bg-panel hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
    >
      <Icon size={16} aria-hidden />
    </button>
  );
}

/** Up / left / right / down in a cross. */
function Pad({ name, actions, v }: { name: string; actions: Action[]; v: Viewer }) {
  const [up, left, right, down] = actions;
  return (
    <div role="group" aria-label={name} className="grid grid-cols-3">
      <span />
      <Button a={up} v={v} />
      <span />
      <Button a={left} v={v} />
      <span className="flex items-center justify-center text-[10px] uppercase text-muted">{name}</span>
      <Button a={right} v={v} />
      <span />
      <Button a={down} v={v} />
      <span />
    </div>
  );
}

export function ViewControls({ viewer }: { viewer: Viewer }) {
  return (
    <div
      role="toolbar"
      aria-label="3D navigation"
      className="absolute right-2 top-2 flex flex-col items-center gap-1 rounded border border-line bg-raised/90 p-1 shadow"
    >
      <div className="flex">
        {ZOOM.map((a) => (
          <Button key={a.label} a={a} v={viewer} />
        ))}
      </div>
      <Pad name="Orbit" actions={ORBIT} v={viewer} />
      <Pad name="Pan" actions={PAN} v={viewer} />
    </div>
  );
}
