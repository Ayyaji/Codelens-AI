import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listClassTests } from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader } from "../components/ui";
import { formatScore, formatWhen } from "../lib/format";

const TYPE_LABEL = { mcq: "MCQ", coding: "Coding", mixed: "Mixed" };

export function classTestAction(test) {
  if (test.can_resume) return { to: `/class-tests/${test.id}`, label: "Resume" };
  if (test.attempt && (test.attempt.status === "submitted" || test.attempt.status === "expired")) {
    return { to: `/class-tests/${test.id}/results`, label: "Results" };
  }
  if (test.can_start) return { to: `/class-tests/${test.id}`, label: "Start" };
  return null;
}

export function ClassTestList({ tests }) {
  if (!tests.length) {
    return <p className="mt-4 text-sm text-faint">No tests are open right now.</p>;
  }
  return (
    <ul className="mt-3 divide-y divide-line">
      {tests.map((test) => {
        const action = classTestAction(test);
        return (
          <li key={test.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-paper">{test.title}</p>
              <p className="mt-1 text-xs text-faint">
                {TYPE_LABEL[test.test_type] || test.test_type} · {test.topic} · {test.duration_minutes} min ·{" "}
                {test.question_count} questions
                {test.attempt?.score != null ? ` · ${formatScore(test.attempt.score)}` : ""}
                {test.available_until ? ` · until ${formatWhen(test.available_until)}` : ""}
              </p>
            </div>
            {action ? (
              <Link to={action.to} className="shrink-0 text-xs text-hint hover:underline">
                {action.label}
              </Link>
            ) : (
              <span className="text-xs text-faint">Closed</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function ClassTestsPage() {
  const [tests, setTests] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    listClassTests()
      .then((rows) => {
        if (!cancel) setTests(rows);
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

  return (
    <div>
      <PageHeader
        kicker="Tests"
        title="Tests your teacher published"
        lede="The clock starts when you press Start. It follows the server deadline, and a late submit grades only the answers that were saved."
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading tests…" /> : null}
      <section className="rounded-xl border border-line bg-panel p-5">
        <ClassTestList tests={tests} />
      </section>
    </div>
  );
}
