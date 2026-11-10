import { Box, TriangleAlert } from "lucide-react";
import { Fragment } from "react";
import { Link } from "react-router";
import type { Citation, CopilotAnswer } from "../api/client";
import { useT } from "../i18n";
import { splitCitations } from "./citations";
import { blocks, inline } from "./markdown";

/** A model answer: light markdown, citation chips that deep-link into the viewer and findings, and the audit trail. */
export function Answer({ a }: { a: CopilotAnswer }) {
  const byId = new Map(a.citations.map((c) => [c.id, c]));
  const { t } = useT();
  const line = (s: string) =>
    splitCitations(s).map((p, i) =>
      p.kind === "text" ? (
        <Fragment key={i}>
          {inline(p.text).map((sp, j) =>
            sp.kind === "b" ? (
              <strong key={j}>{sp.text}</strong>
            ) : sp.kind === "code" ? (
              <code key={j} className="rounded bg-raised px-1 font-mono text-[0.85em]">
                {sp.text}
              </code>
            ) : (
              sp.text
            ),
          )}
        </Fragment>
      ) : (
        <Chip key={i} c={byId.get(p.id)} id={p.id} />
      ),
    );
  return (
    <div className="space-y-3 text-[15px] leading-7">
      {blocks(a.answer).map((b, i) =>
        b.kind === "ul" || b.kind === "ol" ? (
          <List key={i} ordered={b.kind === "ol"}>
            {b.lines.map((l, j) => (
              <li key={j}>{line(l)}</li>
            ))}
          </List>
        ) : (
          <p key={i} className={b.kind === "h" ? "font-semibold" : undefined}>
            {b.lines.map((l, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {line(l)}
              </Fragment>
            ))}
          </p>
        ),
      )}
      {a.unverified.length > 0 && (
        <p role="alert" className="flex items-center gap-1.5 text-xs text-sev-high">
          <TriangleAlert size={14} aria-hidden />{" "}
          {t("Citations removed because tool results did not confirm them: {n}", { n: a.unverified.length })}
        </p>
      )}
      {a.tool_calls.length > 0 && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer select-none">{t("Tool calls: {n}", { n: a.tool_calls.length })}</summary>
          <ol className="mt-1 space-y-0.5 font-mono">
            {a.tool_calls.map((call, i) => (
              <li key={i} className="break-all">
                {call.name}({JSON.stringify(call.input)})
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

const List = ({ ordered, children }: { ordered: boolean; children: React.ReactNode }) =>
  ordered ? <ol className="list-decimal space-y-1 pl-6">{children}</ol> : <ul className="list-disc space-y-1 pl-6">{children}</ul>;

function Chip({ c, id }: { c: Citation | undefined; id: string }) {
  const label = c?.label ?? id.slice(0, 8);
  if (c?.revision_id == null) return <span className="rounded bg-raised px-1 font-mono text-xs">{label}</span>;
  const to =
    c.type === "element"
      ? `/revisions/${c.revision_id}/explorer?focus=${encodeURIComponent(id)}`
      : `/revisions/${c.revision_id}/quality?finding=${encodeURIComponent(id)}`;
  return (
    <Link
      to={to}
      title={`${c.type} ${id}`}
      className="mx-0.5 inline-flex items-center gap-1 rounded-full border border-line bg-raised px-2 align-baseline text-xs leading-5 text-accent hover:border-accent"
    >
      {c.type === "element" && <Box size={12} aria-hidden />}
      {label}
    </Link>
  );
}

/** Answer text with citation markup replaced by labels, for the clipboard. */
export function plainText(a: CopilotAnswer): string {
  const byId = new Map(a.citations.map((c) => [c.id, c.label ?? c.id]));
  return splitCitations(a.answer)
    .map((p) => (p.kind === "text" ? p.text : `[${byId.get(p.id) ?? p.id}]`))
    .join("");
}
