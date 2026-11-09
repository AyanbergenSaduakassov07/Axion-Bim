import { Box, MessageSquareText, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import type { Citation, CopilotAnswer } from "../api/client";
import { useCopilotAsk, useCopilotStatus } from "../api/queries";
import { btn, btnPrimary, ErrorState, input, Panel, Skeleton } from "../ui";
import { splitCitations } from "./citations";

const SUGGESTED = [
  "What changed between the last two revisions?",
  "Why did the health index change?",
  "Which elements are missing a material?",
  "What is the beam volume in the latest revision, and how was it computed?",
];

/** Grounded Q&A over this project's data. Rendered only when the backend has an API key. */
export function CopilotPanel({ projectId }: { projectId: number }) {
  const status = useCopilotStatus();
  const ask = useCopilotAsk(projectId);
  const [question, setQuestion] = useState("");
  if (!status.data?.available) return null;

  const submit = (q: string) => {
    if (q.trim()) ask.mutate(q.trim());
  };
  return (
    <Panel title="Copilot">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
        className="flex gap-2">
        <label htmlFor="copilot-q" className="sr-only">
          Ask about this project
        </label>
        <input
          id="copilot-q"
          className={`${input} flex-1`}
          maxLength={2000}
          placeholder="Ask about revisions, findings, health index or quantities"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className={btnPrimary} disabled={ask.isPending || !question.trim()}>
          <MessageSquareText size={14} aria-hidden /> Ask
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-2">
        {SUGGESTED.map((s) => (
          <button key={s} className={`${btn} h-auto py-1 text-xs`} disabled={ask.isPending} onClick={() => (setQuestion(s), submit(s))}>
            {s}
          </button>
        ))}
      </div>
      <div className="mt-3" aria-live="polite">
        {ask.isPending && <Skeleton rows={3} />}
        {ask.isError && <ErrorState error={ask.error} />}
        {ask.data && <AnswerView a={ask.data} />}
      </div>
      <p className="mt-2 text-xs text-muted">
        Answers come only from Axiom's stored results, cited by element or finding. Sent to {status.data.model}.
      </p>
    </Panel>
  );
}

function AnswerView({ a }: { a: CopilotAnswer }) {
  const byId = new Map(a.citations.map((c) => [c.id, c]));
  return (
    <div className="space-y-2">
      <p className="whitespace-pre-wrap text-sm leading-relaxed">
        {splitCitations(a.answer).map((p, i) =>
          p.kind === "text" ? p.text : <Chip key={i} c={byId.get(p.id)} id={p.id} />,
        )}
      </p>
      {a.unverified.length > 0 && (
        <p role="alert" className="flex items-center gap-1.5 text-xs text-sev-high">
          <TriangleAlert size={14} aria-hidden /> {a.unverified.length} citation(s) could not be verified against tool
          results and were removed.
        </p>
      )}
      <details className="text-xs text-muted">
        <summary className="cursor-pointer">{a.tool_calls.length} tool call(s)</summary>
        <ol className="mt-1 space-y-0.5 font-mono">
          {a.tool_calls.map((t, i) => (
            <li key={i}>
              {t.name}({JSON.stringify(t.input)})
            </li>
          ))}
        </ol>
      </details>
    </div>
  );
}

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
      className="mx-0.5 inline-flex items-center gap-1 rounded border border-line bg-raised px-1.5 text-xs text-accent hover:border-accent"
    >
      {c.type === "element" && <Box size={12} aria-hidden />}
      {label}
    </Link>
  );
}
