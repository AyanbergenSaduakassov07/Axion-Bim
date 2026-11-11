import { FileCheck2, Pencil, Star, Trash2 } from "lucide-react";
import type { IdsEntry } from "../api/client";
import { useState } from "react";
import { useIdsDiff, useIdsLibrary, useIdsMutations } from "../api/queries";
import { useT } from "../i18n";
import { btn, date, ErrorState, input, Panel, Q } from "../ui";

/** Project IDS library (D-34): the client's requirement files, kept once and offered on every upload. */
export function IdsLibrary({ projectId }: { projectId: number }) {
  const q = useIdsLibrary(projectId);
  const { add, setDefault, rename, remove } = useIdsMutations(projectId);
  const { t } = useT();
  return (
    <Panel
      title={t("Requirements (IDS)")}
      actions={
        <label className={btn}>
          {add.isPending ? t("Uploading…") : t("Add IDS file")}
          <input
            type="file"
            accept=".ids,.xml"
            className="sr-only"
            aria-label={t("Add IDS file")}
            disabled={add.isPending}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) add.mutate(f);
              e.target.value = "";
            }}
          />
        </label>
      }
    >
      {add.isError && <ErrorState error={add.error} />}
      <Q q={q} empty={(d) => d.length === 0 && t("No requirement files yet. Add the client's IDS once; every upload can then check against it.")}>
        {(rows: IdsEntry[]) => (
          <ul className="divide-y divide-line text-sm">
            {rows.map((r) => (
              <li key={r.id} className="flex items-center gap-3 py-1.5">
                <FileCheck2 size={14} aria-hidden className="shrink-0 text-muted" />
                <span className="min-w-0 flex-1 truncate font-medium" title={r.ids_hash}>{r.name}</span>
                <span className="shrink-0 text-xs text-muted">{date(r.created_at)}</span>
                <button
                  className={`${btn} shrink-0`}
                  aria-pressed={r.is_default}
                  disabled={setDefault.isPending}
                  onClick={() => setDefault.mutate({ id: r.id, is_default: !r.is_default })}
                >
                  <Star size={12} aria-hidden className={r.is_default ? "fill-accent text-accent" : ""} />
                  {r.is_default ? t("Default for uploads") : t("Make default")}
                </button>
                <button
                  className={`${btn} shrink-0`}
                  aria-label={t("Rename {name}", { name: r.name })}
                  title={t("Rename")}
                  onClick={() => {
                    const name = window.prompt(t("Rename"), r.name)?.trim();
                    if (name && name !== r.name) rename.mutate({ id: r.id, name });
                  }}
                >
                  <Pencil size={12} aria-hidden />
                </button>
                <button
                  className={`${btn} shrink-0`}
                  aria-label={t("Remove {name}", { name: r.name })}
                  title={t("Remove")}
                  onClick={() => {
                    if (window.confirm(t("Remove “{name}” from the library? Past audits keep their results.", { name: r.name }))) remove.mutate(r.id);
                  }}
                >
                  <Trash2 size={12} aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Q>
      {(q.data?.length ?? 0) > 1 && <IdsCompare projectId={projectId} entries={q.data!} />}
    </Panel>
  );
}

/** EIR v1 -> v2: which specifications were added, removed or changed. Computed by the backend. */
function IdsCompare({ projectId, entries }: { projectId: number; entries: IdsEntry[] }) {
  const { t } = useT();
  const [base, setBase] = useState<number>();
  const [head, setHead] = useState<number>();
  const d = useIdsDiff(projectId, head, base).data;
  const pick = (label: string, value: number | undefined, set: (v: number | undefined) => void) => (
    <label className="flex items-center gap-2">
      {label}
      <select className={`${input} text-fg`} value={value ?? ""} onChange={(e) => set(e.target.value ? Number(e.target.value) : undefined)}>
        <option value="">—</option>
        {entries.map((e) => (
          <option key={e.id} value={e.id}>
            {e.name}
          </option>
        ))}
      </select>
    </label>
  );
  const list = (title: string, items: { key: string; name: string; parts?: string[] }[]) =>
    items.length > 0 && (
      <div>
        <div className="text-xs text-muted">{title}</div>
        <ul className="list-disc pl-5">
          {items.map((s) => (
            <li key={s.key}>
              {s.name}{" "}
              <span className="text-xs text-muted">
                {s.key !== s.name && s.key} {s.parts?.join(", ")}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  return (
    <div className="space-y-2 border-t border-line px-3 py-2 text-sm" data-testid="ids-compare">
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
        {pick(t("Compare requirements: from"), base, setBase)}
        {pick(t("to"), head, setHead)}
      </div>
      {d && (
        <>
          {list(t("Added specifications"), d.added)}
          {list(t("Removed specifications"), d.removed)}
          {list(t("Changed specifications"), d.changed)}
          <p className="text-xs text-muted">{t("{n} specifications unchanged", { n: d.unchanged })}</p>
        </>
      )}
    </div>
  );
}
