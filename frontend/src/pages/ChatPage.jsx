import { useState } from "react";
import { ask } from "../api/client";
import { DIRECTIVE_COPY, DirectiveBadge } from "../components/DirectiveBadge";
import { ErrorBanner, LoadingLine, PageHeader, btn, field } from "../components/ui";

const ACCENT = {
  full: "border-l-full",
  hint: "border-l-hint",
  gentle: "border-l-gentle",
  break: "border-l-break",
};

function accentFor(directive) {
  return ACCENT[String(directive || "").toLowerCase()] || "border-l-line";
}

const STARTERS = [
  "Why does subscripting None raise TypeError?",
  "Give me a hint on when to use an inner join.",
  "I keep missing the same SQL filter. What should I do?",
];

let turnId = 0;

export function ChatPage() {
  const [query, setQuery] = useState("");
  const [chatId, setChatId] = useState("");
  const [turns, setTurns] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(text) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setQuery("");
    setError("");
    setBusy(true);
    const mine = { id: `u-${++turnId}`, role: "user", text: trimmed };
    setTurns((current) => [...current, mine]);
    try {
      const data = await ask({ query: trimmed, chatId: chatId || undefined });
      if (data.chat_id) setChatId(data.chat_id);
      setTurns((current) => [
        ...current,
        {
          id: `a-${++turnId}`,
          role: "assistant",
          text: typeof data.answer === "string" ? data.answer : String(data.answer ?? ""),
          directive: data.directive,
          agent: data.agent_used,
        },
      ]);
    } catch (err) {
      setError(err.message || "The guidance chat could not reach POST /ask.");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    send(query);
  }

  const latest = [...turns].reverse().find((turn) => turn.role === "assistant");

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        kicker="05  Guidance"
        title="Ask while you practise"
        lede="This chat calls POST /ask on the live API. Each reply carries a directive — full, hint, gentle, or break — and that badge is the one the server sent."
      />
      <ul className="mb-6 grid gap-2 sm:grid-cols-2">
        {Object.entries(DIRECTIVE_COPY).map(([key, copy]) => (
          <li key={key} className="rounded-lg border border-line bg-panel px-3 py-2">
            <DirectiveBadge directive={key} />
            <p className="mt-2 text-xs leading-relaxed text-mute">{copy}</p>
          </li>
        ))}
      </ul>
      {latest ? (
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-line bg-panel px-4 py-3">
          <DirectiveBadge directive={latest.directive} />
          <p className="text-xs text-mute">Latest reply{latest.agent ? ` · ${latest.agent}` : ""}</p>
        </div>
      ) : null}
      <ErrorBanner message={error} />
      <div className="space-y-3">
        {turns.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line px-4 py-8 text-center text-sm text-faint">
            No messages yet. The badges above are the four directives. A reply will wear the one returned in{" "}
            <span className="font-mono">directive</span>.
          </p>
        ) : null}
        {turns.map((turn) =>
          turn.role === "user" ? (
            <p key={turn.id} className="rounded-lg border border-line bg-panel px-4 py-3 font-mono text-[13px] text-mute">
              {turn.text}
            </p>
          ) : (
            <article
              key={turn.id}
              className={`rounded-lg border border-line border-l-4 bg-panel px-4 py-3 ${accentFor(turn.directive)}`}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <DirectiveBadge directive={turn.directive} />
                {turn.agent ? <span className="font-mono text-[11px] text-faint">{turn.agent}</span> : null}
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{turn.text}</p>
            </article>
          ),
        )}
        {busy ? <LoadingLine label="Waiting on /ask…" /> : null}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {STARTERS.map((starter) => (
          <button key={starter} type="button" className="rounded-full border border-line px-3 py-1 text-xs text-mute hover:text-paper" onClick={() => send(starter)} disabled={busy}>
            {starter}
          </button>
        ))}
      </div>
      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3">
        <label htmlFor="guidance-query" className="sr-only">
          Question
        </label>
        <textarea
          id="guidance-query"
          className={`${field} min-h-24 font-mono text-[13px]`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask about a bug, a concept, or the skill you just missed."
        />
        <div className="flex justify-end">
          <button type="submit" className={btn} disabled={busy || !query.trim()}>
            {busy ? "Sending…" : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}
