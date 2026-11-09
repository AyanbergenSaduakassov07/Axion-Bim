// Fragments cache keyed by IFC sha256. Every call degrades to "no cache" (private mode, quota, blocked storage).
const DB = "axiom-viewer";
const STORE = "fragments";
export const FORMAT = "frag-3.6.1"; // bump when @thatopen/fragments changes so stale buffers are never loaded

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx<T>(mode: IDBTransactionMode, op: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return open().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const req = op(db.transaction(STORE, mode).objectStore(STORE));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      }).finally(() => db.close()),
  );
}

export async function getCached(sha: string): Promise<Uint8Array | null> {
  try {
    const v = await tx<unknown>("readonly", (s) => s.get(`${sha}:${FORMAT}`));
    return v instanceof Uint8Array ? v : null;
  } catch (e) {
    console.warn("[viewer] cache read failed", e);
    return null;
  }
}

export async function putCached(sha: string, data: Uint8Array): Promise<void> {
  try {
    await tx("readwrite", (s) => s.put(data, `${sha}:${FORMAT}`));
  } catch (e) {
    console.warn("[viewer] cache write failed", e);
  }
}
