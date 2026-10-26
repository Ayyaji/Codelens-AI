import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { getClassTest, runClassCode, saveClassAnswers, startClassTest, submitClassTest } from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader, btn, btnGhost } from "../components/ui";
import { formatClock } from "../lib/format";

function useServerCountdown(deadline, serverNow) {
  const skew = useRef(0);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!serverNow) return;
    const parsed = new Date(serverNow).getTime();
    if (!Number.isNaN(parsed)) skew.current = parsed - Date.now();
  }, [serverNow]);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);
  if (!deadline) return null;
  const end = new Date(deadline).getTime();
  if (Number.isNaN(end)) return null;
  return Math.max(0, end - (now + skew.current));
}

function answerPayload(questions, answers) {
  return questions.map((question) => {
    const stored = answers[question.id] || {};
    if (question.type === "mcq") return { question_id: question.id, selected: stored.selected ?? null };
    if (question.type === "short") return { question_id: question.id, text: stored.text ?? "" };
    return {
      question_id: question.id,
      code: stored.code ?? question.starter_code ?? "",
      language: "python",
    };
  });
}

function answersFromServer(questions, saved) {
  const next = {};
  const byId = {};
  for (const item of saved || []) byId[item.question_id] = item;
  for (const question of questions) {
    const item = byId[question.id] || {};
    if (question.type === "mcq") next[question.id] = { selected: item.selected || "" };
    else if (question.type === "short") next[question.id] = { text: item.text || "" };
    else next[question.id] = { code: item.code || question.starter_code || "" };
  }
  return next;
}

export function ClassTakePage() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const [paper, setPaper] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [saveState, setSaveState] = useState("");
  const dirty = useRef(false);
  const fired = useRef(false);
  const remaining = useServerCountdown(paper?.status === "in_progress" ? paper.deadline : null, paper?.server_now);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    getClassTest(testId)
      .then((view) => {
        if (cancel) return;
        if (view.status === "submitted" || view.status === "expired") {
          navigate(`/class-tests/${testId}/results`, { replace: true });
          return;
        }
        setPaper(view);
        setAnswers(answersFromServer(view.questions || [], view.answers));
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not open this test.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [testId, navigate]);

  useEffect(() => {
    if (!paper || paper.status !== "in_progress" || !dirty.current) return undefined;
    const handle = setTimeout(() => {
      const payload = answerPayload(paper.questions || [], answers);
      saveClassAnswers(testId, payload)
        .then((saved) => {
          dirty.current = false;
          setSaveState("Saved");
          if (saved?.server_now) setPaper((current) => (current ? { ...current, server_now: saved.server_now } : current));
        })
        .catch((err) => {
          if (err.status === 409) {
            fired.current = true;
            navigate(`/class-tests/${testId}/results`, { replace: true });
            return;
          }
          setSaveState(err.message || "Could not save");
        });
    }, 800);
    return () => clearTimeout(handle);
  }, [answers, paper, testId, navigate]);

  async function begin() {
    setStarting(true);
    setError("");
    try {
      const view = await startClassTest(testId);
      setPaper(view);
      setAnswers(answersFromServer(view.questions || [], view.answers));
      dirty.current = true;
    } catch (err) {
      if (err.status === 409) navigate(`/class-tests/${testId}/results`);
      else setError(err.message || "Could not start this test.");
    } finally {
      setStarting(false);
    }
  }

  async function submit() {
    if (submitting || !paper) return;
    setSubmitting(true);
    setError("");
    const payload = answerPayload(paper.questions || [], answers);
    try {
      await saveClassAnswers(testId, payload);
    } catch (err) {
      if (err.status !== 409) {
        setError(err.message || "Could not save before submit.");
        setSubmitting(false);
        return;
      }
    }
    try {
      await submitClassTest(testId, payload);
      navigate(`/class-tests/${testId}/results`);
    } catch (err) {
      if (err.status === 409) navigate(`/class-tests/${testId}/results`);
      else {
        fired.current = false;
        setError(err.message || "Could not submit.");
        setSubmitting(false);
      }
    }
  }

  useEffect(() => {
    if (remaining === 0 && paper?.status === "in_progress" && !fired.current) {
      fired.current = true;
      submit();
    }
    // submit reads the latest answers on the render where the timer hits zero
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining]);

  if (loading) {
    return <LoadingLine label="Opening the test…" />;
  }
  if (!paper) {
    return (
      <div>
        <ErrorBanner message={error || "This test is not available."} />
        <Link to="/class-tests" className={btnGhost}>
          Back to tests
        </Link>
      </div>
    );
  }

  if (paper.status !== "in_progress") {
    return (
      <div>
        <PageHeader
          kicker={paper.test_type}
          title={paper.title}
          lede={paper.description || `${paper.duration_minutes} minutes · ${paper.question_count} questions. The timer starts when you press Start.`}
        />
        <ErrorBanner message={error} />
        <button type="button" className={btn} onClick={begin} disabled={starting || !paper.can_start}>
          {starting ? "Starting…" : paper.can_start ? "Start" : "Not open"}
        </button>
      </div>
    );
  }

  const lowTime = remaining !== null && remaining < 60 * 1000;
  const questions = paper.questions || [];

  function updateAnswer(id, patch) {
    dirty.current = true;
    setSaveState("Saving…");
    setAnswers((current) => ({ ...current, [id]: { ...current[id], ...patch } }));
  }

  return (
    <div>
      <PageHeader
        kicker={`${paper.topic} · ${paper.test_type}`}
        title={paper.title}
        lede={paper.description || "Answers save on their own. When the timer hits zero the paper submits what was saved."}
        actions={
          <div className="flex items-center gap-3">
            <p className="font-mono text-[11px] text-faint">{saveState}</p>
            <p className={`font-mono text-2xl tabular-nums ${lowTime ? "text-break" : "text-paper"}`} aria-live="polite">
              {remaining === null ? "--:--" : formatClock(remaining)}
            </p>
            <button type="button" className={btn} onClick={submit} disabled={submitting}>
              {submitting ? "Submitting…" : "Submit"}
            </button>
          </div>
        }
      />
      <ErrorBanner message={error} />
      {submitting ? <LoadingLine label="Scoring the attempt…" /> : null}
      <div className="space-y-4">
        {questions.map((question, index) => (
          <QuestionCard
            key={question.id}
            index={index}
            question={question}
            answer={answers[question.id] || {}}
            onChange={(patch) => updateAnswer(question.id, patch)}
            testId={testId}
          />
        ))}
      </div>
    </div>
  );
}

function QuestionCard({ index, question, answer, onChange, testId }) {
  return (
    <article className="rounded-xl border border-line bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-hint">{question.skill}</p>
        <p className="font-mono text-[11px] text-faint">
          {index + 1} · {question.type}
        </p>
      </div>
      <h3 className="mt-2 whitespace-pre-wrap text-sm font-medium leading-relaxed">{question.prompt}</h3>
      {question.type === "mcq" ? (
        <ul className="mt-3 space-y-2">
          {(question.options || []).map((option) => {
            const selected = answer.selected === option;
            return (
              <li key={option}>
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => onChange({ selected: option })}
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
      ) : null}
      {question.type === "short" ? (
        <textarea
          className="mt-3 min-h-24 w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-paper outline-none focus:border-hint"
          value={answer.text || ""}
          onChange={(event) => onChange({ text: event.target.value })}
          placeholder="Your answer"
        />
      ) : null}
      {question.type === "coding" ? (
        <CodingAnswer testId={testId} question={question} code={answer.code ?? question.starter_code ?? ""} onChange={onChange} />
      ) : null}
    </article>
  );
}

function CodingAnswer({ testId, question, code, onChange }) {
  const [running, setRunning] = useState(false);
  const [cases, setCases] = useState([]);
  const [runError, setRunError] = useState("");

  async function onRun() {
    setRunning(true);
    setRunError("");
    try {
      const result = await runClassCode(testId, { questionId: question.id, code, language: "python" });
      setCases(result.cases);
    } catch (err) {
      setCases([]);
      setRunError(err.message || "Could not run that code.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mt-3 space-y-3">
      {question.signature ? <p className="font-mono text-xs text-mute">{question.signature}</p> : null}
      {(question.visible_cases || []).map((item, index) => (
        <div key={index} className="grid gap-2 sm:grid-cols-2">
          <pre className="overflow-x-auto rounded-lg border border-line bg-ink p-3 font-mono text-xs text-mute">
            <span className="text-faint">visible stdin{"\n"}</span>
            {item.stdin}
          </pre>
          <pre className="overflow-x-auto rounded-lg border border-line bg-ink p-3 font-mono text-xs text-mute">
            <span className="text-faint">expected stdout{"\n"}</span>
            {item.expected}
          </pre>
        </div>
      ))}
      <div className="overflow-hidden rounded-xl border border-line">
        <Editor
          height="220px"
          language="python"
          theme="codelens"
          value={code}
          onChange={(value) => onChange({ code: value ?? "" })}
          options={{
            fontSize: 13,
            fontFamily: '"JetBrains Mono", ui-monospace, monospace',
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
          }}
        />
      </div>
      {running ? <LoadingLine label="Running visible cases…" /> : null}
      {runError ? <ErrorBanner message={runError} /> : null}
      {cases.map((item) => (
        <p key={item.index} className={`font-mono text-xs ${item.passed ? "text-ok" : "text-break"}`}>
          Case {item.index + 1}: {item.passed ? "passed" : "failed"}
          {item.stdout ? ` · stdout ${item.stdout.trim()}` : ""}
        </p>
      ))}
      <div className="flex justify-end">
        <button type="button" className={btnGhost} onClick={onRun} disabled={running}>
          {running ? "Running…" : "Run"}
        </button>
      </div>
    </div>
  );
}
