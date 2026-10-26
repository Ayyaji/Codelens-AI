import { useEffect, useState } from "react";
import { getActivity } from "../api/client";
import { activityLine, activityType, formatWhen } from "../lib/format";
import { ErrorBanner, LoadingLine } from "./ui";

export function ActivityFeed({ limit = 50 }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;

    async function load() {
      try {
        const data = await getActivity(limit);
        if (cancel) return;
        setItems(data);
        setError("");
        setUpdatedAt(new Date());
      } catch (err) {
        if (!cancel) setError(err.message || "Could not load activity.");
      } finally {
        if (!cancel) setLoading(false);
      }
    }

    load();
    const id = window.setInterval(load, 5000);
    return () => {
      cancel = true;
      window.clearInterval(id);
    };
  }, [limit]);

  return (
    <section aria-label="Activity feed">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-faint">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-ok" />
          Live
        </p>
        <p className="text-xs text-faint">{updatedAt ? `Updated ${formatWhen(updatedAt)}` : "Waiting for the first poll"}</p>
      </div>
      <ErrorBanner message={error} />
      {loading && !items.length ? <LoadingLine label="Loading activity…" /> : null}
      {!loading && !items.length && !error ? (
        <p className="rounded-xl border border-dashed border-line px-4 py-8 text-center text-sm text-faint">No student activity yet.</p>
      ) : null}
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-panel">
        {items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3">
            <div className="min-w-0">
              <p className="text-sm text-paper">
                <span className="font-medium">{item.name || "Student"}</span>
                <span className="text-mute"> · {activityLine(item)}</span>
              </p>
              {item.email ? <p className="truncate font-mono text-[11px] text-faint">{item.email}</p> : null}
            </div>
            <div className="text-right">
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-hint">{activityType(item.type)}</p>
              <p className="text-xs text-faint">{formatWhen(item.ts)}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
