import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { runCode, submitTest } from "../api/client";
import { TerminalView } from "../components/TerminalView";
import { ErrorBanner, LoadingLine, PageHeader, btn, btnGhost } from "../components/ui";
import { formatClock } from "../lib/format";
import { useSession } from "../session";

function useCountdown(deadline) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!deadline) return undefined;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [deadline]);
  if (!deadline) return null;
  return Math.max(0, deadline - now);
}

export function TestPage() {
  const { session, setAnswer, setResult } = useSession();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const fired = useRef(false);
  const remaining = useCountdown(session.deadline);

  const questions = session.questions;
  const mcq = questions.filter((question) => question.type === "mcq");
  const coding = questions.filter((question) => question.type === "coding");

  async function submit() {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    const answers = questions.map((question) => {
      const stored = session.answers[question.id] || {};
      if (question.type === "mcq") {
        return { question_id: question.id, selected: stored.selected ?? null };
      }
      return {
        question_id: question.id,
        code: stored.code ?? question.starter_code ?? "",
        language: stored.language || question.language || "python",
      };
    });
    try {
      const result = await submitTest({
        jdId: session.jdId,
        answers,
      });
      setResult(result);
      navigate("/results");
    } catch (err) {
      fired.current = false;
      setError(err.message || "Could not submit the test.");
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (remaining === 0 && questions.length && !fired.current && !session.result) {
      fired.current = true;
      submit();
    }
    // submit closes over the latest answers via the render that sees remaining === 0
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining]);

  if (!questions.length) {
    return (
      <div>
        <PageHeader
          kicker="03  Test"
          title="No test yet"
          lede="Generate a test from the analysed job description. MCQs and a coding task will land here."
        />
        <Link to={session.jdId ? "/analysis" : "/upload"} className={btn}>
          {session.jdId ? "Back to analysis" : "Upload a posting"}
        </Link>
      </div>
    );
  }

  const unanswered = questions.filter((question) => {
    const stored = session.answers[question.id];
    if (question.type === "mcq") return !stored?.selected;
    return !String(stored?.code || "").trim();
  }).length;

  const lowTime = remaining !== null && remaining < 2 * 60 * 1000;

  return (
    <div>
      <PageHeader
        kicker="03  Test"
        title="Practice against this posting"
        lede={`${mcq.length} multiple choice · ${coding.length} coding · answers stay in this browser until you submit`}
        actions={
          <div className="flex items-center gap-3">
            <p
              className={`font-mono text-2xl tabular-nums ${lowTime ? "text-break" : "text-paper"}`}
              aria-label={session.result ? "Submitted" : remaining === null ? "No timer" : `Time remaining ${formatClock(remaining)}`}
            >
              {session.result ? "Done" : remaining === null ? "--:--" : formatClock(remaining)}
            </p>
            <button
              type="button"
              className={btn}
              disabled={submitting}
              onClick={() => {
                if (unanswered > 0) setConfirming(true);
                else submit();
              }}
            >
              {submitting ? "Submitting…" : "Submit"}
            </button>
          </div>
        }
      />
      <ErrorBanner message={error} />
      {submitting ? <LoadingLine label="Scoring the attempt…" /> : null}
      {confirming ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-full/40 bg-full/10 px-4 py-3 text-sm">
          <p>{unanswered} question{unanswered === 1 ? "" : "s"} still unanswered. Submit anyway?</p>
          <div className="flex gap-2">
            <button type="button" className={btnGhost} onClick={() => setConfirming(false)}>
              Keep working
            </button>
            <button type="button" className={btn} onClick={submit} disabled={submitting}>
              Submit anyway
            </button>
          </div>
        </div>
      ) : null}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <section className="space-y-3">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Multiple choice</h2>
          {mcq.map((question, index) => (
            <article key={question.id} className="rounded-xl border border-line bg-panel p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-hint">{question.skill}</p>
                <p className="font-mono text-[11px] text-faint">
                  {index + 1} / {mcq.length}
                </p>
              </div>
              <h3 className="mt-2 text-sm font-medium leading-relaxed">{question.prompt}</h3>
              <ul className="mt-3 space-y-2">
                {(question.options || []).map((option) => {
                  const selected = session.answers[question.id]?.selected === option;
                  return (
                    <li key={option}>
                      <button
                        type="button"
                        aria-pressed={selected}
                        onClick={() => setAnswer(question.id, { selected: option })}
                        className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                          selected ? "border-hint bg-hint/10 text-paper" : "border-line text-mute hover:border-faint hover:text-paper"
                        }`}
                      >
                        {option}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </article>
          ))}
        </section>
        <CodingColumn questions={coding} answers={session.answers} onAnswer={setAnswer} />
      </div>
    </div>
  );
}

function CodingColumn({ questions, answers, onAnswer }) {
  const [activeId, setActiveId] = useState(questions[0]?.id || "");
  const question = questions.find((item) => item.id === activeId) || questions[0];
  const [running, setRunning] = useState(false);
  const [stdout, setStdout] = useState("");
  const [stderr, setStderr] = useState("");
  const [runError, setRunError] = useState("");

  useEffect(() => {
    setStdout("");
    setStderr("");
    setRunError("");
  }, [question?.id]);

  if (!question) {
    return (
      <section className="rounded-xl border border-line bg-panel p-4 text-sm text-mute">
        This test has no coding question.
      </section>
    );
  }

  const code = answers[question.id]?.code ?? question.starter_code ?? "";
  const language = question.language || "python";

  async function onRun() {
    if (!String(code).trim()) {
      setStdout("");
      setStderr("");
      setRunError("Write some Python before running it.");
      return;
    }
    setRunning(true);
    setRunError("");
    setStdout("");
    setStderr("");
    try {
      const result = await runCode({
        code,
        language,
        stdin: question.sample_input ?? "",
      });
      setStdout(result.stdout || "");
      setStderr(result.stderr || "");
    } catch (err) {
      setStdout("");
      setStderr("");
      setRunError(err.message || "Could not run that code.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="space-y-3 lg:sticky lg:top-20">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Coding</h2>
        {questions.length > 1 ? (
          <div className="flex gap-1">
            {questions.map((item, index) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveId(item.id)}
                className={`rounded-md px-2 py-1 font-mono text-[11px] ${
                  item.id === question.id ? "bg-panel text-paper" : "text-faint hover:text-paper"
                }`}
              >
                {index + 1}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <article className="rounded-xl border border-line bg-panel p-4">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-hint">{question.skill}</p>
        <p className="mt-2 text-sm leading-relaxed">{question.prompt}</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <pre className="overflow-x-auto rounded-lg border border-line bg-ink p-3 font-mono text-xs text-mute">
            <span className="text-faint">sample stdin · sent with Run{"\n"}</span>
            {question.sample_input ?? ""}
          </pre>
          <pre className="overflow-x-auto rounded-lg border border-line bg-ink p-3 font-mono text-xs text-mute">
            <span className="text-faint">expected stdout{"\n"}</span>
            {question.sample_output ?? ""}
          </pre>
        </div>
      </article>
      <div className="overflow-hidden rounded-xl border border-line">
        <Editor
          height="220px"
          language={language === "py" ? "python" : language}
          theme="codelens"
          value={code}
          onChange={(value) => onAnswer(question.id, { code: value ?? "", language })}
          options={{
            fontSize: 13,
            fontFamily: '"JetBrains Mono", ui-monospace, monospace',
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            padding: { top: 12, bottom: 12 },
            automaticLayout: true,
            tabSize: 4,
          }}
        />
      </div>
      {running ? <LoadingLine label="Running in the sandbox…" /> : null}
      <TerminalView text={stdout} stderr={stderr} />
      {runError ? <ErrorBanner message={runError} /> : null}
      <div className="flex justify-end">
        <button type="button" className={btnGhost} onClick={onRun} disabled={running}>
          {running ? "Running…" : "Run"}
        </button>
      </div>
    </section>
  );
}
