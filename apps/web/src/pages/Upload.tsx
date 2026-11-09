import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, FileUp, LoaderCircle } from "lucide-react";
import { useEffect, useState, type DragEvent } from "react";
import { Link, useParams } from "react-router";
import { postForm } from "../api/client";
import { useJob } from "../api/queries";
import { btnPrimary, ErrorState, Panel } from "../ui";

async function upload(modelId: number, ifc: File, ids: File | null, geometry: boolean) {
  const form = new FormData();
  form.append("file", ifc);
  form.append("geometry", String(geometry));
  if (ids) {
    const idsForm = new FormData();
    idsForm.append("file", ids);
    form.append("ids_hash", (await postForm<{ ids_hash: string }>("/ids", idsForm)).ids_hash);
  }
  return (await postForm<{ job_id: number }>(`/models/${modelId}/revisions`, form)).job_id;
}

export function Upload() {
  const modelId = Number(useParams().modelId);
  const [ifc, setIfc] = useState<File | null>(null);
  const [ids, setIds] = useState<File | null>(null);
  const [geometry, setGeometry] = useState(true);
  const [over, setOver] = useState(false);
  const m = useMutation({ mutationFn: () => upload(modelId, ifc!, ids, geometry) });

  const drop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setIfc(f);
  };
  const submit = (e: { preventDefault(): void }) => {
    e.preventDefault();
    if (ifc) m.mutate();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-lg font-semibold">Upload revision</h1>
      <form onSubmit={submit} className="space-y-4">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={drop}
          className={`flex cursor-pointer flex-col items-center gap-2 rounded border-2 border-dashed px-4 py-10 text-sm ${over ? "border-accent bg-raised" : "border-line bg-panel"}`}
        >
          <FileUp size={24} className="text-muted" aria-hidden />
          <span>{ifc ? `${ifc.name} (${(ifc.size / 1e6).toFixed(2)} MB)` : "Drop an .ifc file here, or click to choose"}</span>
          <input type="file" accept=".ifc" className="sr-only" aria-label="IFC file" onChange={(e) => setIfc(e.target.files?.[0] ?? null)} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="block text-xs text-muted">IDS file (optional)</span>
            <input type="file" accept=".ids,.xml" aria-label="IDS file" className="text-sm" onChange={(e) => setIds(e.target.files?.[0] ?? null)} />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={geometry} onChange={(e) => setGeometry(e.target.checked)} />
            Compute geometry volumes (slower)
          </label>
        </div>
        <button className={btnPrimary} disabled={!ifc || m.isPending || m.isSuccess}>
          {m.isPending ? "Uploading…" : "Upload and audit"}
        </button>
      </form>
      {m.isError && <ErrorState error={m.error} />}
      {m.data != null && <JobStatus jobId={m.data} />}
    </div>
  );
}

function JobStatus({ jobId }: { jobId: number }) {
  const q = useJob(jobId);
  const qc = useQueryClient();
  const job = q.data;
  const result = job?.result as { revision_id?: number; created?: boolean } | null | undefined;
  useEffect(() => {
    if (job?.status === "done") qc.invalidateQueries({ queryKey: ["revisions"] });
  }, [job?.status, qc]);

  return (
    <Panel title={`Job ${jobId}`}>
      <div aria-live="polite" className="space-y-2 text-sm">
        {q.isError && <ErrorState error={q.error} retry={() => q.refetch()} />}
        {(!job || job.status === "queued" || job.status === "running") && !q.isError && (
          <p className="flex items-center gap-2">
            <LoaderCircle size={16} className="animate-spin text-accent" aria-hidden />
            {job?.status === "running" ? "Extracting, auditing and comparing…" : "Queued…"}
          </p>
        )}
        {job?.status === "error" && <ErrorState error={new Error(job.error_message ?? "Processing failed.")} />}
        {job?.status === "done" && result?.revision_id != null && (
          <div className="space-y-2">
            <p className="flex items-center gap-2">
              <CircleCheck size={16} className="text-ok" aria-hidden />
              Done{result.created === false ? " — identical file, existing revision reused" : ""}.
            </p>
            <Link className={btnPrimary} to={`/revisions/${result.revision_id}/quality`}>
              Open Quality Center
            </Link>
          </div>
        )}
      </div>
    </Panel>
  );
}
