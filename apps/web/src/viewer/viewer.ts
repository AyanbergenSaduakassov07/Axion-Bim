// The only module that touches ThatOpen. Pages speak GlobalIds; localIds never leave this file.
import * as OBC from "@thatopen/components";
import * as FRAGS from "@thatopen/fragments";
import * as THREE from "three";
import { getCached, putCached } from "./cache";

export type FocusResult = "ok" | "no_geometry" | "not_found";
export type LoadStats = { ms: number; cached: boolean; bytes: number };
export type Viewer = {
  load(fileUrl: string, sha: string, onProgress?: (p: number) => void): Promise<LoadStats>;
  /** Replace all highlights: one colour per group of GlobalIds. Empty map clears. */
  highlight(groups: Map<string, string[]>): Promise<void>;
  focus(globalId: string): Promise<FocusResult>;
  /** Show only these elements; null shows everything again. */
  isolate(globalIds: string[] | null): Promise<void>;
  setClassVisibility(ifcClass: string, visible: boolean): Promise<void>;
  onSelect(cb: (globalId: string | null) => void): () => void;
  dispose(): void;
};

const FOCUS_COLOR = "#ffb300";
const FIT_PADDING = 1.5; // single-element boxes frame too tightly without it

const material = (color: string): FRAGS.MaterialDefinition => ({
  color: new THREE.Color(color),
  renderedFaces: FRAGS.RenderedFaces.TWO,
  opacity: 1,
  transparent: false,
});

function createWorld(el: HTMLElement) {
  const components = new OBC.Components();
  const world = components.get(OBC.Worlds).create<OBC.SimpleScene, OBC.OrthoPerspectiveCamera, OBC.SimpleRenderer>();
  world.scene = new OBC.SimpleScene(components);
  world.scene.setup();
  world.scene.three.background = null; // let the panel colour show through
  world.renderer = new OBC.SimpleRenderer(components, el);
  world.camera = new OBC.OrthoPerspectiveCamera(components);
  components.init();
  components.get(OBC.Grids).create(world);
  const fragments = components.get(OBC.FragmentsManager);
  fragments.init("/fragments-worker.mjs");
  const onCameraUpdate = () => {
    fragments.core.update().catch(() => {});
  };
  world.camera.controls.addEventListener("update", onCameraUpdate);
  return { components, world, fragments, onCameraUpdate };
}

function convert(bytes: ArrayBuffer, onProgress?: (p: number) => void): Promise<Uint8Array> {
  const worker = new Worker(new URL("./convert.worker.ts", import.meta.url), { type: "module" });
  return new Promise<Uint8Array>((resolve, reject) => {
    worker.onmessage = (e) => {
      if (e.data.progress != null) onProgress?.(e.data.progress);
      else if (e.data.done) resolve(e.data.done);
      else reject(new Error(`IFC conversion failed: ${e.data.error}`));
    };
    worker.onerror = (e) => reject(new Error(`IFC conversion worker crashed: ${e.message}`));
    worker.postMessage(bytes, [bytes]);
  }).finally(() => worker.terminate());
}

async function fetchBytes(url: string): Promise<ArrayBuffer> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Could not download the model file (HTTP ${r.status}).`);
  return r.arrayBuffer();
}

export function createViewer(el: HTMLElement): Viewer {
  const { components, world, fragments, onCameraUpdate } = createWorld(el);
  let disposed = false;
  let model: FRAGS.FragmentsModel | null = null;
  let painted = new Map<number, string>(); // localId → highlight colour, so focus can restore it
  let focused: { id: number; guid: string } | null = null;
  const listeners = new Set<(g: string | null) => void>();

  const isModelNotFound = (err: unknown) =>
    String((err as Error)?.message ?? err).includes("Fragments: Model not found");

  const onUnhandledRejection = (event: PromiseRejectionEvent) => {
    if (disposed && isModelNotFound(event.reason)) {
      event.preventDefault();
    }
  };
  window.addEventListener("unhandledrejection", onUnhandledRejection);

  const need = () => {
    if (!model) throw new Error("No model loaded.");
    return model;
  };
  const ids = async (guids: string[]) =>
    (await need().getLocalIdsByGuids(guids)).filter((x): x is number => x != null);
  const render = () => fragments.core.update(true).catch(() => {});

  async function restore(id: number) {
    const color = painted.get(id);
    if (color) await need().highlight([id], material(color));
    else await need().resetHighlight([id]);
  }

  async function fit(localIds: number[]) {
    const box = await need().getMergedBox(localIds);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    sphere.radius *= FIT_PADDING;
    await world.camera.controls.fitToSphere(sphere, true);
  }

  async function select(guid: string | null, id: number | null) {
    if (focused) await restore(focused.id);
    focused = guid != null && id != null ? { id, guid } : null;
    if (focused) await need().highlight([focused.id], material(FOCUS_COLOR));
    await render();
  }

  const canvas = world.renderer!.three.domElement;
  const mouse = new THREE.Vector2();
  const onClick = async (e: MouseEvent) => {
    if (!model) return;
    mouse.set(e.clientX, e.clientY);
    const hit = await model.raycast({ camera: world.camera.three, mouse, dom: canvas });
    const guid = hit ? ((await model.getGuidsByLocalIds([hit.localId]))[0] ?? null) : null;
    await select(guid, guid ? hit!.localId : null);
    listeners.forEach((cb) => cb(guid));
  };
  canvas.addEventListener("click", onClick);

  const viewer: Viewer = {
    async load(fileUrl, sha, onProgress) {
      if (disposed) return { ms: 0, cached: false, bytes: 0 };
      const t0 = performance.now();
      let buf = await getCached(sha);
      const cached = buf != null;
      if (!buf) {
        buf = await convert(await fetchBytes(fileUrl), onProgress);
        if (disposed) return { ms: 0, cached: false, bytes: 0 };
        await putCached(sha, buf);
      }
      if (disposed) return { ms: 0, cached: false, bytes: 0 };
      const bytes = buf.byteLength;
      try {
        model = await fragments.core.load(buf, { modelId: sha, camera: world.camera.three });
        if (disposed) return { ms: 0, cached, bytes };
        world.scene.three.add(model.object);
        await fit(await model.getItemsIdsWithGeometry());
        await render();
      } catch (err: unknown) {
        if (disposed && isModelNotFound(err)) {
          return { ms: 0, cached, bytes };
        }
        throw err;
      }
      const stats = { ms: Math.round(performance.now() - t0), cached, bytes };
      exposeTestHook(viewer, () => focused?.guid ?? null, stats);
      return stats;
    },
    async highlight(groups) {
      const m = need();
      await m.resetHighlight();
      painted = new Map();
      for (const [color, guids] of groups) {
        const local = await ids(guids);
        local.forEach((id) => painted.set(id, color));
        if (local.length) await m.highlight(local, material(color));
      }
      if (focused) await m.highlight([focused.id], material(FOCUS_COLOR));
      await render();
    },
    async focus(guid) {
      const [id] = await ids([guid]);
      if (id == null) return "not_found";
      if (!(await need().getItemsIdsWithGeometry()).includes(id)) {
        await select(null, null);
        return "no_geometry";
      }
      await select(guid, id);
      await fit([id]);
      return "ok";
    },
    async isolate(guids) {
      const m = need();
      if (guids == null) await m.resetVisible();
      else {
        await m.setVisible(undefined, false);
        await m.setVisible(await ids(guids), true);
      }
      await render();
    },
    async setClassVisibility(ifcClass, visible) {
      const m = need();
      const byCat = await m.getItemsOfCategories([new RegExp(`^${ifcClass}$`, "i")]);
      await m.setVisible(Object.values(byCat).flat(), visible);
      await render();
    },
    onSelect(cb) {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      canvas.removeEventListener("click", onClick);
      world.camera.controls.removeEventListener("update", onCameraUpdate);
      listeners.clear();
      if (import.meta.env.DEV) delete (window as unknown as Record<string, unknown>).__axiomViewer;
      components.dispose();
      setTimeout(() => {
        window.removeEventListener("unhandledrejection", onUnhandledRejection);
      }, 5000);
    },
  };
  return viewer;
}

/** Dev-only hook for Playwright and the load/memory measurement (P10 §6). */
function exposeTestHook(v: Viewer, lastFocused: () => string | null, stats: LoadStats) {
  if (!import.meta.env.DEV) return;
  const mem = (performance as { memory?: { usedJSHeapSize: number } }).memory;
  (window as unknown as Record<string, unknown>).__axiomViewer = {
    focus: v.focus,
    lastFocused,
    stats,
    heapMB: mem ? Math.round(mem.usedJSHeapSize / 1e6) : null,
  };
}
