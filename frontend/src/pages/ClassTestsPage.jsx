import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listClassTests } from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader } from "../components/ui";
import { formatLead, formatScore, formatWhen } from "../lib/format";

const TYPE_LABEL = { mcq: "MCQ", coding: "Coding", mixed: "Mixed" };
const TABS = [
  { id: "active", label: "Active" },
  { id: "upcoming", label: "Upcoming" },
  { id: "completed", label: "Completed" },
];

function finished(test) {
  const status = test.attempt?.status;
  return status === "submitted" || status === "expired";
}

export function classTestPhase(test) {
  if (test.phase === "upcoming" || test.phase === "active" || test.phase === "completed" || test.phase === "closed") {
    return test.phase;
  }
  if (test.can_resume || test.can_start) return "active";
  if (finished(test)) return "completed";
  return "upcoming";
}

export function classTestAction(test) {
  if (test.can_resume) return { to: `/class-tests/${test.id}`, label: "Resume" };
  if (test.can_start) return { to: `/class-tests/${test.id}`, label: "Start" };
  if (finished(test)) return { to: `/class-tests/${test.id}/results`, label: "Results" };
  if (classTestPhase(test) === "upcoming") return { to: `/class-tests/${test.id}`, label: "View" };
  return null;
}

function useNow(serverNow) {
  const [now, setNow] = useState(() => Date.now());
  const [skew, setSkew] = useState(0);
  useEffect(() => {
    if (!serverNow) return;
    const parsed = new Date(serverNow).getTime();
    if (!Number.isNaN(parsed)) setSkew(parsed - Date.now());
  }, [serverNow]);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now + skew;
}

function StartCountdown({ iso, now }) {
  if (!iso) return null;
  const start = new Date(iso).getTime();
  if (Number.isNaN(start)) return null;
  const left = start - now;
  if (left <= 0) return <span>Open now</span>;
  return <span>Starts in {formatLead(left)}</span>;
}

export function ClassTestList({ tests, serverNow, showClosed = false, empty = "No tests are open right now." }) {
  const now = useNow(serverNow || tests.serverNow);
  const visible = showClosed ? tests : tests.filter((test) => classTestPhase(test) !== "closed");
  if (!visible.length) {
    return <p className="mt-4 text-sm text-faint">{empty}</p>;
  }
  return (
    <ul className="mt-3 divide-y divide-line">
      {visible.map((test) => {
        const action = classTestAction(test);
        const phase = classTestPhase(test);
        const results = finished(test) ? `/class-tests/${test.id}/results` : "";
        return (
          <li key={test.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-paper">{test.title}</p>
              <p className="mt-1 text-xs text-faint">
                {TYPE_LABEL[test.test_type] || test.test_type} · {test.topic} · {test.duration_minutes} min ·{" "}
                {test.question_count} questions
                {test.attempt?.score != null ? ` · ${formatScore(test.attempt.score)}` : ""}
                {phase === "upcoming" ? (
                  <>
                    {" · "}
                    <StartCountdown iso={test.available_from} now={now} />
                  </>
                ) : null}
                {phase !== "upcoming" && test.available_until ? ` · until ${formatWhen(test.available_until)}` : ""}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {results && action?.label !== "Results" ? (
                <Link to={results} className="text-xs text-faint hover:underline">
                  Results
                </Link>
              ) : null}
              {action ? (
                <Link to={action.to} className="text-xs text-hint hover:underline">
                  {action.label}
                </Link>
              ) : (
                <span className="text-xs text-faint">Closed</span>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function ClassTestsPage() {
  const [tests, setTests] = useState([]);
  const [serverNow, setServerNow] = useState(null);
  const [tab, setTab] = useState("active");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    listClassTests()
      .then((rows) => {
        if (cancel) return;
        setTests(rows);
        setServerNow(rows.serverNow || null);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load tests.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  const counts = { active: 0, upcoming: 0, completed: 0 };
  for (const test of tests) {
    const phase = classTestPhase(test);
    if (phase === "completed" || (finished(test) && phase !== "upcoming")) counts.completed += 1;
    if (phase === "active" || test.can_start || test.can_resume) counts.active += 1;
    if (phase === "upcoming") counts.upcoming += 1;
  }
  const shown = tests.filter((test) => {
    const phase = classTestPhase(test);
    if (tab === "upcoming") return phase === "upcoming";
    if (tab === "completed") return phase === "completed" || (finished(test) && !test.can_resume);
    return phase === "active" || test.can_start || test.can_resume;
  });

  return (
    <div>
      <PageHeader
        kicker="Tests"
        title="Tests your teacher published"
        lede="Active tests can be started. Upcoming tests show the countdown until the window opens. The clock itself starts when you press Start."
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading tests…" /> : null}
      <div className="mb-4 flex gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-lg px-3 py-1.5 text-sm ${tab === item.id ? "bg-hint text-ink" : "border border-line text-mute"}`}
          >
            {item.label}
            <span className="ml-2 font-mono text-[11px]">{counts[item.id]}</span>
          </button>
        ))}
      </div>
      <section className="rounded-xl border border-line bg-panel p-5">
        <ClassTestList
          tests={shown}
          serverNow={serverNow}
          showClosed={tab === "completed"}
          empty={tab === "upcoming" ? "No tests are scheduled." : tab === "completed" ? "No finished tests yet." : "No tests are open right now."}
        />
      </section>
    </div>
  );
}
