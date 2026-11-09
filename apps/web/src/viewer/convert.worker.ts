// IFC → Fragments conversion off the main thread.
import * as FRAGS from "@thatopen/fragments";

self.onmessage = async (e: MessageEvent<ArrayBuffer>) => {
  try {
    const importer = new FRAGS.IfcImporter();
    importer.wasm = { path: "/wasm/", absolute: true };
    const out = await importer.process({
      bytes: new Uint8Array(e.data),
      progressCallback: (progress) => self.postMessage({ progress }),
    });
    self.postMessage({ done: out }, { transfer: [out.buffer] });
  } catch (err) {
    self.postMessage({ error: err instanceof Error ? err.message : String(err) });
  }
};
