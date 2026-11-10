import { ArrowUp, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useCopilotStatus } from "../api/queries";
import { useT } from "../i18n";
import { btn, Panel } from "../ui";

export const SUGGESTED = [
  "What changed between the last two revisions?",
  "Why did the health index change?",
  "Which elements are missing a material?",
  "What is the beam volume in the latest revision, and how was it computed?",
];

/** Entry point on the project page: a question here opens the full chat. Rendered only when the backend has a key. */
export function CopilotPanel({ projectId }: { projectId: number }) {
  const status = useCopilotStatus();
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const { t } = useT();
  if (!status.data?.available) return null;

  const open = (q: string) => q.trim() && navigate(`/projects/${projectId}/copilot?q=${encodeURIComponent(q.trim())}`);
  return (
    <Panel
      title={t("Copilot")}
      actions={
        <Link to={`/projects/${projectId}/copilot`} className={`${btn} h-7 text-xs`}>
          {t("Open chats")}
        </Link>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          open(question);
        }}
        data-composer
        className="flex items-center gap-2 rounded-3xl border border-line bg-bg p-1.5 pl-4 focus-within:border-accent"
      >
        <Sparkles size={16} className="shrink-0 text-accent" aria-hidden />
        <label htmlFor="copilot-q" className="sr-only">
          {t("Ask about this project")}
        </label>
        <input
          id="copilot-q"
          className="h-8 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
          maxLength={2000}
          placeholder={t("Ask about revisions, findings, health index or quantities")}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          aria-label={t("Ask")}
          disabled={!question.trim()}
          className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-full bg-fg text-bg disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ArrowUp size={16} aria-hidden />
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-2">
        {SUGGESTED.map((en) => (
          <button key={en} className={`${btn} h-auto rounded-full py-1 text-xs`} onClick={() => open(t(en))}>
            {t(en)}
          </button>
        ))}
      </div>
    </Panel>
  );
}
