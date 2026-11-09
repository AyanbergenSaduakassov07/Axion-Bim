// Spike: load IFC → fragments, click → GlobalId, GlobalId → highlight + fit. Exposes window.__axiomViewer for e2e.
import * as THREE from "three";
import * as OBC from "@thatopen/components";
import * as FRAGS from "@thatopen/fragments";

const $ = (id: string) => document.getElementById(id)!;
const log = (m: string) => { $("log").textContent += m + "\n"; console.log("[axiom]", m); };

const components = new OBC.Components();
const world = components.get(OBC.Worlds).create<OBC.SimpleScene, OBC.OrthoPerspectiveCamera, OBC.SimpleRenderer>();
world.scene = new OBC.SimpleScene(components);
world.scene.setup();
world.renderer = new OBC.SimpleRenderer(components, $("vp"));
world.camera = new OBC.OrthoPerspectiveCamera(components);
components.init();
components.get(OBC.Grids).create(world);

const fragments = components.get(OBC.FragmentsManager);
fragments.init("/fragments-worker.mjs");
world.camera.controls.addEventListener("update", () => fragments.core.update());
fragments.list.onItemSet.add(({ value: model }) => {
  model.useCamera(world.camera.three);
  world.scene.three.add(model.object);
  fragments.core.update(true);
});

const ifcLoader = components.get(OBC.IfcLoader);
await ifcLoader.setup({ autoSetWasm: false, wasm: { path: "/wasm/", absolute: true } });

const t0 = performance.now();
const buf = new Uint8Array(await (await fetch("/sample.ifc")).arrayBuffer());
const model = await ifcLoader.load(buf, true, "sample");
const loadMs = Math.round(performance.now() - t0);
log(`loaded in ${loadMs} ms`);
await world.camera.controls.fitToBox(await model.getMergedBox(await model.getItemsIdsWithGeometry()), false);

const hl: FRAGS.MaterialDefinition = { color: new THREE.Color("#ffb300"), renderedFaces: FRAGS.RenderedFaces.TWO, opacity: 1, transparent: false };
let current: number[] = [];
async function select(ids: number[]) {
  if (current.length) await model.resetHighlight(current);
  current = ids;
  if (ids.length) await model.highlight(ids, hl);
  await fragments.core.update(true);
}

async function focus(guid: string): Promise<boolean> {
  const [id] = await model.getLocalIdsByGuids([guid]);
  if (id == null) { log(`GlobalId ${guid} not found`); return false; }
  const withGeo = new Set(await model.getItemsIdsWithGeometry());
  if (!withGeo.has(id)) { log(`${guid} has no renderable geometry`); return false; }
  await select([id]);
  await world.camera.controls.fitToBox(await model.getMergedBox([id]), true);
  log(`focused ${guid} (localId ${id})`);
  return true;
}

const mouse = new THREE.Vector2();
$("vp").addEventListener("click", async (e) => {
  mouse.set(e.clientX, e.clientY);
  const hit = await model.raycast({ camera: world.camera.three, mouse, dom: world.renderer!.three.domElement });
  if (!hit) { await select([]); $("clicked").textContent = "—"; return; }
  const [guid] = await model.getGuidsByLocalIds([hit.localId]);
  $("clicked").textContent = guid ?? `(no guid, localId ${hit.localId})`;
  await select([hit.localId]);
});
$("go").addEventListener("click", () => focus(($("guid") as HTMLInputElement).value.trim()));

(window as any).__axiomViewer = { focus, loadMs, lastFocused: () => current };
$("status").textContent = "ready";
