import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { downloadClassScores, getClassAttempts } from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader, btnGhost } from "../components/ui";
import { formatScore, formatWhen } from "../lib/format";

function taken(seconds) {
  if (seconds == null) return "—";
  const total = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}m ${String(rest).padStart(2, "0")}s`;
}

function answerText(question, saved) {
  if (!saved) return "—";
  if (question?.type === "mcq") return saved.selected || "—";
  if (question?.type === "short") return saved.text || "—";
  const code = saved.code || "";
  if (!code.trim()) return "—";
  return code.length > 280 ? `${code.slice(0, 280)}…` : code;
}

export function TeacherTestResultsPage() {
  const { testId } = useParams();
  const [report, setReport] = useState(null);
  const [openId, setOpenId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let cancel = false;
    getClassAttempts(testId)
      .then((next) => {
        if (!cancel) setReport(next);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load results.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [testId]);

  async function exportCsv() {
    setExporting(true);
    setError("");
    try {
      const csv = await downloadClassScores(testId);
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${(report?.test?.title || "class-test").replace(/[^\w.-]+/g, "-")}-scores.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || "Could not export scores.");
    } finally {
      setExporting(false);
    }
  }

  const test = report?.test;
  const attempts = report?.attempts || [];
  const questions = test?.questions || [];
  const byQuestion = Object.fromEntries(questions.map((question) => [question.id, question]));
  const stats = report?.question_stats || [];

  return (
    <div>
      <PageHeader
        kicker="Results"
        title={test?.title || "Test results"}
        lede="Scores, time taken, tab switches, and each student's answers. Question edits stay locked once an attempt exists."
        actions={
          <>
            <button type="button" className={btnGhost} onClick={exportCsv} disabled={exporting || !report}>
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
            <Link to={`/dashboard/tests/${testId}`} className={btnGhost}>
              Edit test
            </Link>
          </>
        }
      />
      <ErrorBanner message={error} />
      {loading ? <LoadingLine label="Loading attempts…" /> : null}
      {report ? (
        <div className="mb-4 grid gap-3 sm:grid-cols-3">
          <Stat label="Attempts" value={report.count} />
          <Stat label="Finished" value={report.submitted} />
          <Stat label="Average" value={formatScore(report.average_score)} />
        </div>
      ) : null}
      {stats.length ? (
        <section className="mb-4 rounded-xl border border-line bg-panel p-4">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Per question</h2>
          <ul className="mt-3 space-y-3">
            {stats.map((item, index) => (
              <li key={item.question_id}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <p className="min-w-0 text-paper">
                    <span className="text-faint">{index + 1}. </span>
                    {(item.prompt || "").split("\n")[0]}
                  </p>
                  <p className="shrink-0 font-mono text-xs text-mute">
                    {item.percent_correct == null ? "—" : `${item.percent_correct}%`} correct
                    <span className="text-faint"> · {item.correct}/{item.graded}</span>
                  </p>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink">
                  <div className="h-full bg-hint" style={{ width: `${Math.max(0, Math.min(100, Number(item.percent_correct) || 0))}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <div className="overflow-x-auto rounded-xl border border-line">
        <table className="w-full min-w-[48rem] text-left text-sm">
          <thead className="bg-panel text-[11px] uppercase tracking-[0.14em] text-faint">
            <tr>
              <th className="px-4 py-3 font-medium">Student</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Score</th>
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Tab switches</th>
              <th className="px-4 py-3 font-medium">Submitted</th>
            </tr>
          </thead>
          <tbody>
            {attempts.map((attempt) => (
              <Fragment key={attempt.id}>
                <tr
                  className="cursor-pointer border-t border-line hover:bg-panel"
                  onClick={() => setOpenId((current) => (current === attempt.id ? "" : attempt.id))}
                >
                  <td className="px-4 py-3">
                    <span className="block font-medium text-paper">{attempt.student?.name}</span>
                    <span className="block font-mono text-[11px] text-faint">{attempt.student?.email}</span>
                  </td>
                  <td className="px-4 py-3 text-mute">{attempt.status}</td>
                  <td className="px-4 py-3 font-mono text-paper">{formatScore(attempt.score)}</td>
                  <td className="px-4 py-3 font-mono text-mute">{taken(attempt.time_taken_seconds)}</td>
                  <td className="px-4 py-3 font-mono text-mute">{attempt.focus_loss_count || 0}</td>
                  <td className="px-4 py-3 text-mute">{formatWhen(attempt.submitted_at)}</td>
                </tr>
                {openId === attempt.id ? (
                  <tr className="border-t border-line">
                    <td colSpan={6} className="bg-ink px-4 py-3">
                      <ul className="space-y-3">
                        {(attempt.results || []).map((result) => {
                          const question = byQuestion[result.question_id];
                          const saved = (attempt.answers || []).find((item) => item.question_id === result.question_id);
                          return (
                            <li key={result.question_id} className="text-xs text-mute">
                              <p>
                                <span className={result.correct ? "text-ok" : "text-break"}>
                                  {result.correct ? "Correct" : "Missed"}
                                </span>
                                {" · "}
                                {result.skill} · {result.type}
                                {result.type === "coding" ? ` · ${result.passed ?? 0}/${result.total ?? 0}` : ""}
                              </p>
                              <p className="mt-1 whitespace-pre-wrap text-paper">{(question?.prompt || result.question_id).slice(0, 280)}</p>
                              <p className="mt-1 whitespace-pre-wrap text-faint">Answer: {answerText(question, saved)}</p>
                            </li>
                          );
                        })}
                        {!(attempt.results || []).length ? <li className="text-xs text-faint">No score yet.</li> : null}
                      </ul>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
            {!loading && !attempts.length ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-faint">
                  No attempts yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <article className="rounded-xl border border-line bg-panel px-4 py-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">{label}</p>
      <p className="mt-2 font-mono text-3xl text-paper">{value}</p>
    </article>
  );
}
