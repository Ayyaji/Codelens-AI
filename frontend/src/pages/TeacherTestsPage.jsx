import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteClassTest, duplicateClassTest, listTeacherClassTests } from "../api/client";
import { ConfirmDialog, ErrorBanner, LoadingLine, PageHeader, btn, btnGhost } from "../components/ui";
import { formatWhen } from "../lib/format";

const TYPE_LABEL = { mcq: "MCQ", coding: "Coding", mixed: "Mixed" };

export function TeacherTestsPage() {
  const [tests, setTests] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  function load() {
    setLoading(true);
    listTeacherClassTests()
      .then(setTests)
      .catch((err) => setError(err.message || "Could not load tests."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function duplicate(test) {
    setError("");
    try {
      const copy = await duplicateClassTest(test.id);
      navigate(`/dashboard/tests/${copy.id}`);
    } catch (err) {
      setError(err.message || "Could not duplicate that test.");
    }
  }

  async function confirmDelete() {
    if (!pending) return;
    setBusy(true);
    try {
      await deleteClassTest(pending.id);
      setPending(null);
      load();
    } catch (err) {
      setError(err.message || "Could not delete that test.");
      setPending(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Tests"
        title="Class tests"
        lede="MCQ, coding, or mixed. Set the minutes and the window, then publish. Students do not see the answer key."
        actions={
          <Link to="/dashboard/tests/new" className={btn}>
            New test
          </Link>
        }
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading tests…" /> : null}
      <div className="overflow-x-auto rounded-xl border border-line">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead className="bg-panel text-[11px] uppercase tracking-[0.14em] text-faint">
            <tr>
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Minutes</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Updated</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {tests.map((test) => (
              <tr key={test.id} className="border-t border-line">
                <td className="px-4 py-3">
                  <span className="block font-medium text-paper">{test.title}</span>
                  <span className="block text-xs text-faint">
                    {test.topic} · {test.question_count} questions
                  </span>
                </td>
                <td className="px-4 py-3 text-mute">{TYPE_LABEL[test.test_type] || test.test_type}</td>
                <td className="px-4 py-3 font-mono text-paper">{test.duration_minutes}</td>
                <td className="px-4 py-3">
                  <span className={`font-mono text-[10px] uppercase tracking-[0.12em] ${test.published ? "text-ok" : "text-faint"}`}>
                    {test.published ? "Published" : "Draft"}
                  </span>
                  {test.attempt_count ? (
                    <span className="mt-1 block text-[11px] text-faint">
                      {test.attempt_count} attempt{test.attempt_count === 1 ? "" : "s"}
                    </span>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-mute">{formatWhen(test.updated_at)}</td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/dashboard/tests/${test.id}/results`} className="mr-3 text-xs text-hint hover:underline">
                    Results
                  </Link>
                  <Link to={`/dashboard/tests/${test.id}`} className="mr-3 text-xs text-hint hover:underline">
                    Edit
                  </Link>
                  <button type="button" className="mr-3 text-xs text-hint hover:underline" onClick={() => duplicate(test)}>
                    Duplicate
                  </button>
                  <button type="button" className="text-xs text-faint hover:text-break" onClick={() => setPending(test)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {!loading && !tests.length ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-faint">
                  No tests yet.{" "}
                  <Link to="/dashboard/tests/new" className="text-hint hover:underline">
                    Create one
                  </Link>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={Boolean(pending)}
        title="Delete this test?"
        body={pending ? `“${pending.title}” is removed only when nobody has attempted it. Otherwise unpublish it.` : ""}
        confirmLabel="Delete"
        danger
        busy={busy}
        onConfirm={confirmDelete}
        onClose={() => setPending(null)}
      />
      <p className="mt-4 text-xs text-faint">
        <Link to="/dashboard" className={btnGhost}>
          Back to overview
        </Link>
      </p>
    </div>
  );
}
