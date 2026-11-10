import { FileCheck2, Star } from "lucide-react";
import type { IdsEntry } from "../api/client";
import { useIdsLibrary, useIdsMutations } from "../api/queries";
import { useT } from "../i18n";
import { btn, date, ErrorState, Panel, Q } from "../ui";

/** Project IDS library (D-34): the client's requirement files, kept once and offered on every upload. */
export function IdsLibrary({ projectId }: { projectId: number }) {
  const q = useIdsLibrary(projectId);
  const { add, setDefault } = useIdsMutations(projectId);
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
              </li>
            ))}
          </ul>
        )}
      </Q>
    </Panel>
  );
}
