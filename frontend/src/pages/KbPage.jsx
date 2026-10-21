import { useEffect, useState } from "react";
import { approveKb, listPendingKb, rejectKb, updateKb } from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader, btn, btnDanger, btnGhost } from "../components/ui";
import { formatWhen } from "../lib/format";

export function KbPage() {
  const [items, setItems] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");

  useEffect(() => {
    let cancel = false;
    listPendingKb()
      .then((data) => {
        if (cancel) return;
        setItems(data);
        const next = {};
        for (const item of data) next[item.id] = item.content;
        setDrafts(next);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load pending notes.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  function drop(id) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  async function save(item) {
    const content = (drafts[item.id] ?? item.content).trim();
    if (!content) {
      setError("The note needs some text.");
      return null;
    }
    if (content === item.content) return item;
    const updated = await updateKb(item.id, content);
    setItems((current) => current.map((row) => (row.id === item.id ? updated : row)));
    setDrafts((current) => ({ ...current, [item.id]: updated.content }));
    return updated;
  }

  async function onSave(item) {
    setBusyId(item.id);
    setError("");
    try {
      await save(item);
    } catch (err) {
      setError(err.message || "Could not save that note.");
    } finally {
      setBusyId("");
    }
  }

  async function onApprove(item) {
    setBusyId(item.id);
    setError("");
    try {
      const content = (drafts[item.id] ?? item.content).trim();
      if (content !== item.content) await save(item);
      await approveKb(item.id);
      drop(item.id);
    } catch (err) {
      setError(err.message || "Could not approve that note.");
    } finally {
      setBusyId("");
    }
  }

  async function onReject(item) {
    setBusyId(item.id);
    setError("");
    try {
      await rejectKb(item.id);
      drop(item.id);
    } catch (err) {
      setError(err.message || "Could not reject that note.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Knowledge"
        title="Notes waiting for review"
        lede="Web-agent text stays here until you approve it. Editing and rejecting do not write the note into the knowledge base. Approve is the only call that does."
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading pending notes…" /> : null}
      {!loading && !items.length ? (
        <p className="rounded-xl border border-dashed border-line px-4 py-10 text-center text-sm text-faint">
          Nothing is waiting for review.
        </p>
      ) : null}
      <ul className="space-y-4">
        {items.map((item) => {
          const draft = drafts[item.id] ?? item.content;
          const dirty = draft.trim() !== item.content;
          const locked = busyId === item.id;
          return (
            <li key={item.id} className="rounded-xl border border-line bg-panel p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm font-medium text-paper">{item.query || "Untitled query"}</p>
                <p className="text-xs text-faint">{formatWhen(item.created_at)}</p>
              </div>
              <p className="mt-1 font-mono text-[11px] text-faint">
                {item.source || "source unknown"}
                {item.proposed_by ? ` · proposed by ${item.proposed_by}` : ""}
              </p>
              <label className="mt-4 block text-xs text-mute" htmlFor={`kb-${item.id}`}>
                Note
                <textarea
                  id={`kb-${item.id}`}
                  className="mt-2 min-h-32 w-full rounded-lg border border-line bg-ink px-3 py-2.5 font-mono text-[13px] leading-relaxed text-paper outline-none focus:border-hint"
                  value={draft}
                  onChange={(event) => setDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                />
              </label>
              <div className="mt-3 flex flex-wrap justify-end gap-2">
                <button type="button" className={btnGhost} disabled={!dirty || locked} onClick={() => onSave(item)}>
                  {locked ? "Working…" : "Save edit"}
                </button>
                <button type="button" className={btnDanger} disabled={locked} onClick={() => onReject(item)}>
                  Reject
                </button>
                <button type="button" className={btn} disabled={locked} onClick={() => onApprove(item)}>
                  Approve
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
