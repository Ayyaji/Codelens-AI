import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getHistory, getPersona, listMyChats } from "../api/client";
import { PersonaPanel } from "../components/PersonaPanel";
import { ErrorBanner, LoadingLine, PageHeader, btn, btnGhost } from "../components/ui";
import { formatScore, formatWhen } from "../lib/format";
import { useSession } from "../session";

export function MySpacePage() {
  const { setUpload } = useSession();
  const navigate = useNavigate();
  const [chats, setChats] = useState([]);
  const [persona, setPersona] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    Promise.all([listMyChats(), getPersona(), getHistory()])
      .then(([nextChats, nextPersona, nextHistory]) => {
        if (cancel) return;
        setChats(nextChats);
        setPersona(nextPersona);
        setHistory(nextHistory);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load My Space.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  function openJd(jd) {
    setUpload({ jdId: jd.jd_id, sourceLabel: jd.filename });
    navigate("/analysis");
  }

  const jds = history?.jds || [];
  const tests = history?.tests || [];

  return (
    <div>
      <PageHeader
        kicker="My Space"
        title="Pick up where you left off"
        lede="Chats stay attached to a chat id, so opening one continues the same guidance thread. The persona is the latest weak topics, mistake patterns, and scores."
        actions={
          <>
            <Link to="/chat" className={btnGhost}>
              New chat
            </Link>
            <Link to="/upload" className={btn}>
              Upload a posting
            </Link>
          </>
        }
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading your space…" /> : null}
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="rounded-xl border border-line bg-panel p-5">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Chats</h2>
          {chats.length ? (
            <ul className="mt-3 divide-y divide-line">
              {chats.map((chat) => (
                <li key={chat.chat_id}>
                  <Link to={`/chat/${encodeURIComponent(chat.chat_id)}`} className="block py-3 hover:text-hint">
                    <span className="block text-sm font-medium text-paper">{chat.title}</span>
                    <span className="mt-1 block text-xs text-faint">{formatWhen(chat.updated_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : loading ? null : (
            <p className="mt-4 rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm text-faint">
              No chats yet. Start one from Guidance.
            </p>
          )}
        </section>
        {persona ? <PersonaPanel persona={persona} /> : <div />}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-panel p-5">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Job descriptions</h2>
          {jds.length ? (
            <ul className="mt-3 divide-y divide-line">
              {jds.map((jd) => (
                <li key={jd.jd_id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-paper">{jd.filename}</p>
                    <p className="text-xs text-faint">{formatWhen(jd.created_at)}</p>
                  </div>
                  <button type="button" className="shrink-0 text-xs text-hint hover:underline" onClick={() => openJd(jd)}>
                    Open
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-faint">No postings yet.</p>
          )}
        </section>
        <section className="rounded-xl border border-line bg-panel p-5">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Tests</h2>
          {tests.length ? (
            <ul className="mt-3 divide-y divide-line">
              {tests.map((test) => (
                <li key={test.test_id} className="flex items-center justify-between gap-3 py-3">
                  <p className="text-sm text-mute">{formatWhen(test.created_at)}</p>
                  <p className="font-mono text-sm text-paper">{formatScore(test.score)}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-faint">No scored attempts yet.</p>
          )}
        </section>
      </div>
    </div>
  );
}
