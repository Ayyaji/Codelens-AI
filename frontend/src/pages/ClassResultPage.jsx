import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getClassTest } from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader, btnGhost } from "../components/ui";
import { formatScore } from "../lib/format";

function taken(seconds) {
  if (seconds == null) return "—";
  const total = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}m ${String(rest).padStart(2, "0")}s`;
}

export function ClassResultPage() {
  const { testId } = useParams();
  const [paper, setPaper] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    getClassTest(testId)
      .then((view) => {
        if (!cancel) setPaper(view);
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load this result.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [testId]);

  if (loading) return <LoadingLine label="Loading the result…" />;
  if (!paper || (paper.status !== "submitted" && paper.status !== "expired")) {
    return (
      <div>
        <ErrorBanner message={error || "This attempt is not finished."} />
        <Link to={`/class-tests/${testId}`} className={btnGhost}>
          Back to the test
        </Link>
      </div>
    );
  }

  const results = paper.results || [];
  const questions = paper.questions || [];
  const byId = Object.fromEntries(results.map((item) => [item.question_id, item]));

  return (
    <div>
      <PageHeader
        kicker="Result"
        title={paper.title}
        lede={
          paper.status === "expired"
            ? "Time was up. This score uses the answers saved before the deadline."
            : "Submitted before the deadline."
        }
        actions={
          <Link to="/class-tests" className={btnGhost}>
            All tests
          </Link>
        }
      />
      <ErrorBanner message={error} />
      <div className="grid gap-3 sm:grid-cols-3">
        <article className="rounded-xl border border-line bg-panel px-4 py-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Score</p>
          <p className="mt-2 font-mono text-3xl text-paper">{formatScore(paper.score)}</p>
        </article>
        <article className="rounded-xl border border-line bg-panel px-4 py-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Time</p>
          <p className="mt-2 font-mono text-3xl text-paper">{taken(paper.time_taken_seconds)}</p>
        </article>
        <article className="rounded-xl border border-line bg-panel px-4 py-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Answers</p>
          <p className="mt-2 text-sm text-mute">{paper.show_answers ? "Shown below" : "Hidden by your teacher"}</p>
        </article>
      </div>
      <div className="mt-4 space-y-3">
        {questions.map((question, index) => {
          const result = byId[question.id];
          const saved = (paper.answers || []).find((item) => item.question_id === question.id) || {};
          return (
            <article key={question.id} className="rounded-xl border border-line bg-panel p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-hint">
                  {index + 1} · {question.skill}
                </p>
                <p className={`font-mono text-xs ${result?.correct ? "text-ok" : "text-break"}`}>
                  {result?.correct ? "Correct" : "Missed"}
                  {result?.type === "coding" && result.total ? ` · ${result.passed}/${result.total} hidden` : ""}
                </p>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-paper">{question.prompt}</p>
              {question.type === "mcq" ? <p className="mt-2 text-sm text-mute">Your answer: {saved.selected || "—"}</p> : null}
              {question.type === "short" ? <p className="mt-2 text-sm text-mute">Your answer: {saved.text || "—"}</p> : null}
              {paper.show_answers && question.type === "mcq" ? (
                <p className="mt-2 text-sm text-paper">Correct: {question.correct_option || question.options?.[question.correct_index]}</p>
              ) : null}
              {paper.show_answers && question.type === "short" ? (
                <p className="mt-2 text-sm text-paper">Expected: {question.expected}</p>
              ) : null}
              {paper.show_answers && question.explanation ? (
                <p className="mt-2 text-sm leading-relaxed text-mute">{question.explanation}</p>
              ) : null}
              {paper.show_answers && result?.detail ? <p className="mt-2 font-mono text-xs text-faint">{result.detail}</p> : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}
