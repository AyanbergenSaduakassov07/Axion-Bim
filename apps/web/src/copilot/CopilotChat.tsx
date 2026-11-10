import { ArrowLeft, ArrowUp, Check, Copy, MessageSquare, PanelLeft, RotateCcw, Sparkles, SquarePen, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import type { CopilotAnswer } from "../api/client";
import { useCopilotAsk, useCopilotStatus, useProjects } from "../api/queries";
import { useT } from "../i18n";
import { Empty, Skeleton } from "../ui";
import { Answer, plainText } from "./Answer";
import { type Chat, historyOf, lastIndex, loadChats, type Msg, saveChats } from "./chats";
import { SUGGESTED } from "./CopilotPanel";

const newChat = (): Chat => ({ id: crypto.randomUUID(), title: "", updated: Date.now(), messages: [] });

/** Full-page chat over one project's stored results, laid out like familiar AI chat apps. */
export function CopilotChat() {
  const projectId = Number(useParams().projectId);
  const [params, setParams] = useSearchParams();
  const status = useCopilotStatus();
  const project = useProjects().data?.find((p) => p.id === projectId);
  const ask = useCopilotAsk(projectId);
  const { t } = useT();
  const [chats, setChats] = useState<Chat[]>(() => loadChats(projectId));
  const [activeId, setActiveId] = useState<string | null>(null);
  const [sidebar, setSidebar] = useState(true);
  const active = chats.find((c) => c.id === activeId) ?? null;
  const started = useRef(false);

  const update = (change: (prev: Chat[]) => Chat[]) =>
    setChats((prev) => {
      const next = change(prev);
      saveChats(projectId, next);
      return next;
    });

  const send = (question: string, base: Chat | null = active, prior: Msg[] = base?.messages ?? []) => {
    const q = question.trim();
    if (!q || ask.isPending) return;
    const chat = base ?? newChat();
    const asked: Chat = { ...chat, title: chat.title || q.slice(0, 60), updated: Date.now(), messages: [...prior, { role: "user", text: q }] };
    update((prev) => [asked, ...prev.filter((c) => c.id !== chat.id)]);
    setActiveId(chat.id);
    const append = (m: Msg) =>
      update((prev) => prev.map((c) => (c.id === chat.id ? { ...c, messages: [...c.messages, m], updated: Date.now() } : c)));
    ask.mutate(
      { question: q, history: historyOf(prior) },
      { onSuccess: (a) => append({ role: "assistant", answer: a }), onError: (e) => append({ role: "error", text: e.message }) },
    );
  };

  // a question typed on the project page arrives as ?q= and starts a new chat once
  const initial = params.get("q");
  useEffect(() => {
    if (!initial || started.current || !status.data?.available) return;
    started.current = true;
    setParams({}, { replace: true });
    send(initial, null);
  });

  const regenerate = () => {
    if (!active) return;
    const lastUser = lastIndex(active.messages, (m) => m.role === "user");
    const m = active.messages[lastUser];
    if (m?.role === "user") send(m.text, active, active.messages.slice(0, lastUser));
  };

  if (status.isPending) return <Skeleton rows={4} />;
  if (!status.data?.available) return <Empty>{t("Copilot is not configured on this server.")}</Empty>;

  return (
    <div className="-m-4 flex h-[calc(100dvh-2.5rem)] overflow-hidden">
      {sidebar && (
        <aside aria-label={t("Chats")} className="hidden w-64 shrink-0 flex-col border-r border-line bg-panel md:flex">
          <div className="flex items-center gap-1 p-2">
            <IconButton label={t("Hide sidebar")} onClick={() => setSidebar(false)}>
              <PanelLeft size={18} />
            </IconButton>
            <button
              className="ml-auto inline-flex h-9 cursor-pointer items-center gap-2 rounded-lg px-3 text-sm hover:bg-raised"
              onClick={() => setActiveId(null)}
            >
              <SquarePen size={16} aria-hidden /> {t("New chat")}
            </button>
          </div>
          <Link to={`/projects/${projectId}`} className="mx-2 mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted hover:bg-raised hover:text-fg">
            <ArrowLeft size={14} aria-hidden /> <span className="truncate">{project?.name ?? t("Project {id}", { id: projectId })}</span>
          </Link>
          <p className="px-5 pb-1 text-xs font-medium text-muted">{t("Recent")}</p>
          <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
            {chats.length === 0 && <p className="px-3 py-2 text-xs text-muted">{t("No chats yet.")}</p>}
            {chats.map((c) => (
              <div key={c.id} className={`group flex items-center rounded-lg ${c.id === activeId ? "bg-raised" : "hover:bg-raised"}`}>
                <button className="flex-1 cursor-pointer truncate px-3 py-2 text-left text-sm" onClick={() => setActiveId(c.id)} title={c.title}>
                  {c.title || t("New chat")}
                </button>
                <button
                  aria-label={t("Delete chat")}
                  className="mr-1 cursor-pointer rounded p-1 text-muted opacity-0 hover:text-sev-critical focus:opacity-100 group-hover:opacity-100"
                  onClick={() => {
                    update((prev) => prev.filter((x) => x.id !== c.id));
                    if (c.id === activeId) setActiveId(null);
                  }}
                >
                  <Trash2 size={14} aria-hidden />
                </button>
              </div>
            ))}
          </nav>
        </aside>
      )}
      <section className="flex min-w-0 flex-1 flex-col bg-bg">
        <header className="flex h-12 shrink-0 items-center gap-2 px-3">
          {!sidebar && (
            <>
              <IconButton label={t("Show sidebar")} onClick={() => setSidebar(true)}>
                <PanelLeft size={18} />
              </IconButton>
              <IconButton label={t("New chat")} onClick={() => setActiveId(null)}>
                <SquarePen size={18} />
              </IconButton>
            </>
          )}
          <span className="text-sm font-semibold">Axiom Copilot</span>
          <span className="rounded-full border border-line px-2 text-xs text-muted">{status.data.model}</span>
        </header>
        {active ? (
          <Thread messages={active.messages} pending={ask.isPending} onRegenerate={regenerate} />
        ) : (
          <Welcome name={project?.name} onPick={(q) => send(q, null)} disabled={ask.isPending} />
        )}
        <Composer onSend={(q) => send(q)} busy={ask.isPending} />
        <p className="px-4 pb-3 text-center text-xs text-muted">
          {t("Answers come only from Axiom's stored results, cited by element or finding. Sent to {model}.", { model: status.data.model })}
        </p>
      </section>
    </div>
  );
}

function Welcome({ name, onPick, disabled }: { name?: string; onPick: (q: string) => void; disabled: boolean }) {
  const { t } = useT();
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 overflow-y-auto px-4">
      <div className="text-center">
        <Sparkles size={32} className="mx-auto mb-3 text-accent" aria-hidden />
        <h1 className="text-2xl font-semibold">{t("What would you like to know?")}</h1>
        {name && <p className="mt-1 text-sm text-muted">{name}</p>}
      </div>
      <div className="grid w-full max-w-3xl gap-3 sm:grid-cols-2">
        {SUGGESTED.map((en) => (
          <button
            key={en}
            disabled={disabled}
            onClick={() => onPick(t(en))}
            className="flex cursor-pointer items-start gap-2 rounded-2xl border border-line bg-panel p-4 text-left text-sm hover:bg-raised disabled:opacity-50"
          >
            <MessageSquare size={16} className="mt-0.5 shrink-0 text-muted" aria-hidden />
            {t(en)}
          </button>
        ))}
      </div>
    </div>
  );
}

function Thread({ messages, pending, onRegenerate }: { messages: Msg[]; pending: boolean; onRegenerate: () => void }) {
  const end = useRef<HTMLDivElement>(null);
  const { t } = useT();
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);
  const lastAnswer = lastIndex(messages, (m) => m.role !== "user");
  return (
    <div className="flex-1 overflow-y-auto" aria-live="polite">
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[80%] whitespace-pre-wrap rounded-3xl bg-raised px-5 py-2.5 text-[15px] leading-7">{m.text}</p>
            </div>
          ) : (
            <Assistant key={i}>
              {m.role === "assistant" ? (
                <>
                  <Answer a={m.answer} />
                  <Actions a={m.answer} onRegenerate={i === lastAnswer && !pending ? onRegenerate : undefined} />
                </>
              ) : (
                <div role="alert" className="text-sm text-sev-critical">
                  {m.text}
                  {i === lastAnswer && !pending && (
                    <button className="ml-2 cursor-pointer underline" onClick={onRegenerate}>
                      {t("Try again")}
                    </button>
                  )}
                </div>
              )}
            </Assistant>
          ),
        )}
        {pending && (
          <Assistant>
            <span className="flex h-7 items-center gap-1" aria-label={t("Thinking…")}>
              {[0, 150, 300].map((d) => (
                <span key={d} className="size-2 animate-bounce rounded-full bg-muted" style={{ animationDelay: `${d}ms` }} />
              ))}
            </span>
          </Assistant>
        )}
        <div ref={end} />
      </div>
    </div>
  );
}

const Assistant = ({ children }: { children: React.ReactNode }) => (
  <div className="flex gap-4">
    <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border border-line bg-panel">
      <Sparkles size={16} className="text-accent" aria-hidden />
    </span>
    <div className="min-w-0 flex-1">{children}</div>
  </div>
);

function Actions({ a, onRegenerate }: { a: CopilotAnswer; onRegenerate?: () => void }) {
  const { t } = useT();
  const [copied, setCopied] = useState(false);
  const copy = () =>
    navigator.clipboard?.writeText(plainText(a)).then(
      () => (setCopied(true), setTimeout(() => setCopied(false), 1500)),
      () => setCopied(false),
    );
  return (
    <div className="mt-2 flex gap-1 text-muted">
      <IconButton label={copied ? t("Copied") : t("Copy")} onClick={copy}>
        {copied ? <Check size={16} /> : <Copy size={16} />}
      </IconButton>
      {onRegenerate && (
        <IconButton label={t("Regenerate")} onClick={onRegenerate}>
          <RotateCcw size={16} />
        </IconButton>
      )}
    </div>
  );
}

function Composer({ onSend, busy }: { onSend: (q: string) => void; busy: boolean }) {
  const { t } = useT();
  const [text, setText] = useState("");
  const submit = () => {
    if (!text.trim() || busy) return;
    onSend(text);
    setText("");
  };
  return (
    <form
      className="mx-auto w-full max-w-3xl px-4 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div data-composer className="flex items-end gap-2 rounded-3xl border border-line bg-panel p-2 pl-5 shadow-sm focus-within:border-accent">
        <label htmlFor="copilot-chat-q" className="sr-only">
          {t("Message Copilot")}
        </label>
        <textarea
          id="copilot-chat-q"
          rows={1}
          maxLength={2000}
          value={text}
          placeholder={t("Ask about revisions, findings, health index or quantities")}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          className="field-sizing-content max-h-48 min-h-6 flex-1 resize-none bg-transparent py-1.5 text-[15px] outline-none placeholder:text-muted"
        />
        <button
          aria-label={t("Send")}
          disabled={busy || !text.trim()}
          className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-fg text-bg disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ArrowUp size={18} aria-hidden />
        </button>
      </div>
    </form>
  );
}

const IconButton = ({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) => (
  <button type="button" aria-label={label} title={label} onClick={onClick} className="cursor-pointer rounded-lg p-1.5 hover:bg-raised hover:text-fg">
    {children}
  </button>
);
