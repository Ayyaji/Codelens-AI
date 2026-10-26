import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createClassTest,
  getTeacherClassTest,
  importMcqQuestions,
  listQuestionBank,
  updateClassTest,
} from "../api/client";
import { ErrorBanner, LoadingLine, PageHeader, btn, btnGhost, field } from "../components/ui";

const TOPICS = ["DSA", "general", "aptitude", "OOP", "DBMS", "OS", "CN", "complexity"];

function newId() {
  return `q_${Math.random().toString(16).slice(2, 10)}`;
}

function starterFor(signature) {
  const name = signature.replace(/^def\s+/, "").split("(")[0].trim() || "solve";
  const head = signature.trim().endsWith(":") ? signature.trim() : `${signature.trim()}:`;
  return `${head}\n    # your code here\n    raise NotImplementedError\n\nif __name__ == "__main__":\n    import json\n    args = json.loads(input() or "[]")\n    result = ${name}(*args)\n    if isinstance(result, str):\n        print(result)\n    else:\n        print(json.dumps(result, separators=(",", ":")))\n`;
}

function blankQuestion(type) {
  if (type === "coding") {
    return {
      id: newId(),
      type: "coding",
      skill: "arrays",
      prompt: "",
      signature: "def solve(data):",
      language: "python",
      starter_code: starterFor("def solve(data):"),
      visible_cases: [{ stdin: "[]", expected: "" }],
      hidden_cases: [{ stdin: "[]", expected: "" }],
      explanation: "",
    };
  }
  if (type === "short") {
    return { id: newId(), type: "short", skill: "general", prompt: "", expected: "", keywords: [], explanation: "" };
  }
  return {
    id: newId(),
    type: "mcq",
    skill: "general",
    prompt: "",
    options: ["", "", "", ""],
    correct_index: 0,
    explanation: "",
  };
}

function toLocal(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromLocal(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function emptyForm() {
  return {
    title: "",
    description: "",
    topic: "DSA",
    test_type: "mcq",
    duration_minutes: 20,
    available_from: "",
    available_until: "",
    published: false,
    allow_retake: false,
    show_answers_after_submit: false,
    questions: [blankQuestion("mcq")],
  };
}

function fromTest(test) {
  return {
    title: test.title || "",
    description: test.description || "",
    topic: test.topic || "general",
    test_type: test.test_type || "mixed",
    duration_minutes: test.duration_minutes || 20,
    available_from: toLocal(test.available_from),
    available_until: toLocal(test.available_until),
    published: Boolean(test.published),
    allow_retake: Boolean(test.allow_retake),
    show_answers_after_submit: Boolean(test.show_answers_after_submit),
    questions: (test.questions || []).map((question) => ({ ...question, keywords: question.keywords || [] })),
  };
}

function payload(form) {
  return {
    title: form.title.trim(),
    description: form.description.trim(),
    topic: form.topic.trim() || "general",
    test_type: form.test_type,
    duration_minutes: Number(form.duration_minutes),
    available_from: fromLocal(form.available_from),
    available_until: fromLocal(form.available_until),
    published: form.published,
    allow_retake: form.allow_retake,
    show_answers_after_submit: form.show_answers_after_submit,
    questions: form.questions.map((question) => {
      const next = { ...question };
      if (question.type === "short") {
        next.keywords = Array.isArray(question.keywords)
          ? question.keywords
          : String(question.keywords || "")
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean);
      }
      if (question.type === "mcq") next.correct_index = Number(question.correct_index) || 0;
      return next;
    }),
  };
}

export function TeacherTestEditorPage() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const editing = Boolean(testId);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [bankOpen, setBankOpen] = useState(false);
  const [bank, setBank] = useState([]);
  const [paste, setPaste] = useState("");
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (!testId) return undefined;
    let cancel = false;
    getTeacherClassTest(testId)
      .then((test) => {
        if (!cancel) setForm(fromTest(test));
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load that test.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [testId]);

  function patch(partial) {
    setForm((current) => ({ ...current, ...partial }));
  }

  function patchQuestion(index, partial) {
    setForm((current) => {
      const questions = current.questions.slice();
      questions[index] = { ...questions[index], ...partial };
      return { ...current, questions };
    });
  }

  function addQuestion(question) {
    const copy = { ...question, id: question.id && !form.questions.some((item) => item.id === question.id) ? question.id : newId() };
    setForm((current) => ({ ...current, questions: [...current.questions, copy] }));
  }

  async function openBank() {
    setBankOpen(true);
    setError("");
    try {
      const kind = form.test_type === "mixed" ? "" : form.test_type;
      const data = await listQuestionBank({ kind });
      setBank(data.questions || []);
    } catch (err) {
      setError(err.message || "Could not load the question bank.");
    }
  }

  async function bulkAdd() {
    setImporting(true);
    setError("");
    try {
      const questions = await importMcqQuestions({ text: paste });
      setForm((current) => ({ ...current, questions: [...current.questions, ...questions] }));
      setPaste("");
    } catch (err) {
      setError(err.message || "Could not read those questions.");
    } finally {
      setImporting(false);
    }
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body = payload(form);
      if (editing) {
        await updateClassTest(testId, body);
        navigate("/dashboard/tests");
      } else {
        const created = await createClassTest(body);
        navigate(`/dashboard/tests/${created.id}`);
      }
    } catch (err) {
      setError(err.message || "Could not save the test.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingLine label="Loading the test…" />;

  const addType = form.test_type === "coding" ? "coding" : "mcq";

  return (
    <form onSubmit={save}>
      <PageHeader
        kicker="Tests"
        title={editing ? "Edit test" : "New test"}
        lede="Pick MCQ for a quick quiz, Coding for DSA, or Mixed when you want both plus short answers."
        actions={
          <>
            <Link to="/dashboard/tests" className={btnGhost}>
              Cancel
            </Link>
            <button type="submit" className={btn} disabled={saving}>
              {saving ? "Saving…" : form.published ? "Save and publish" : "Save draft"}
            </button>
          </>
        }
      />
      <ErrorBanner message={error} />
      <div className="grid gap-4 lg:grid-cols-2">
        <label className="block text-xs text-mute">
          Title
          <input className={`${field} mt-1`} value={form.title} onChange={(event) => patch({ title: event.target.value })} required />
        </label>
        <label className="block text-xs text-mute">
          Topic
          <input className={`${field} mt-1`} list="test-topics" value={form.topic} onChange={(event) => patch({ topic: event.target.value })} />
          <datalist id="test-topics">
            {TOPICS.map((topic) => (
              <option key={topic} value={topic} />
            ))}
          </datalist>
        </label>
        <label className="block text-xs text-mute lg:col-span-2">
          Description
          <textarea className={`${field} mt-1 min-h-20`} value={form.description} onChange={(event) => patch({ description: event.target.value })} />
        </label>
        <label className="block text-xs text-mute">
          Test type
          <select className={`${field} mt-1`} value={form.test_type} onChange={(event) => patch({ test_type: event.target.value })}>
            <option value="mcq">MCQ</option>
            <option value="coding">Coding</option>
            <option value="mixed">Mixed</option>
          </select>
        </label>
        <label className="block text-xs text-mute">
          Duration (minutes)
          <input
            className={`${field} mt-1`}
            type="number"
            min="1"
            max="240"
            value={form.duration_minutes}
            onChange={(event) => patch({ duration_minutes: event.target.value })}
            required
          />
        </label>
        <label className="block text-xs text-mute">
          Available from
          <input className={`${field} mt-1`} type="datetime-local" value={form.available_from} onChange={(event) => patch({ available_from: event.target.value })} />
        </label>
        <label className="block text-xs text-mute">
          Available until
          <input className={`${field} mt-1`} type="datetime-local" value={form.available_until} onChange={(event) => patch({ available_until: event.target.value })} />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap gap-4 text-sm text-mute">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.published} onChange={(event) => patch({ published: event.target.checked })} />
          Published
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.allow_retake} onChange={(event) => patch({ allow_retake: event.target.checked })} />
          Allow retake
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.show_answers_after_submit}
            onChange={(event) => patch({ show_answers_after_submit: event.target.checked })}
          />
          Show answers after submit
        </label>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Questions</h2>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btnGhost} onClick={() => addQuestion(blankQuestion(addType))}>
            Add {addType === "coding" ? "coding" : "MCQ"}
          </button>
          {form.test_type === "mixed" ? (
            <button type="button" className={btnGhost} onClick={() => addQuestion(blankQuestion("short"))}>
              Add short answer
            </button>
          ) : null}
          <button type="button" className={btnGhost} onClick={openBank}>
            Pick from bank
          </button>
        </div>
      </div>

      {form.test_type !== "coding" ? (
        <div className="mt-4 rounded-xl border border-line bg-panel p-4">
          <p className="text-sm text-paper">Add many MCQs at once</p>
          <p className="mt-1 text-xs text-mute">Paste a JSON array, or questions that start with Q: and options A) B) C) D), then Answer:.</p>
          <textarea className={`${field} mt-3 min-h-28 font-mono text-xs`} value={paste} onChange={(event) => setPaste(event.target.value)} placeholder='[{"prompt":"...","options":["A","B","C","D"],"correct_index":0}]' />
          <button type="button" className={`${btnGhost} mt-3`} onClick={bulkAdd} disabled={importing || !paste.trim()}>
            {importing ? "Reading…" : "Add pasted questions"}
          </button>
        </div>
      ) : null}

      <div className="mt-4 space-y-4">
        {form.questions.map((question, index) => (
          <QuestionEditor
            key={`${question.id}-${index}`}
            question={question}
            onChange={(partial) => patchQuestion(index, partial)}
            onRemove={() => patch({ questions: form.questions.filter((_, item) => item !== index) })}
          />
        ))}
      </div>

      {bankOpen ? (
        <div className="fixed inset-0 z-40 grid place-items-center bg-ink/70 px-4" onClick={() => setBankOpen(false)} role="presentation">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-line bg-panel p-5" onClick={(event) => event.stopPropagation()} role="dialog">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-paper">Question bank</h2>
              <button type="button" className={btnGhost} onClick={() => setBankOpen(false)}>
                Close
              </button>
            </div>
            <ul className="mt-4 divide-y divide-line">
              {bank.map((question) => (
                <li key={question.id} className="flex items-start justify-between gap-3 py-3">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-hint">
                      {question.type} · {question.skill}
                    </p>
                    <p className="mt-1 text-sm text-paper">{question.prompt.slice(0, 180)}</p>
                  </div>
                  <button
                    type="button"
                    className="shrink-0 text-xs text-hint hover:underline"
                    onClick={() => addQuestion(question)}
                  >
                    Add
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </form>
  );
}

function QuestionEditor({ question, onChange, onRemove }) {
  const keywords = Array.isArray(question.keywords) ? question.keywords.join(", ") : question.keywords || "";
  return (
    <article className="rounded-xl border border-line bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-faint">{question.type}</p>
        <button type="button" className="text-xs text-faint hover:text-break" onClick={onRemove}>
          Remove
        </button>
      </div>
      <label className="mt-3 block text-xs text-mute">
        Skill
        <input className={`${field} mt-1`} value={question.skill || ""} onChange={(event) => onChange({ skill: event.target.value })} />
      </label>
      <label className="mt-3 block text-xs text-mute">
        Prompt
        <textarea className={`${field} mt-1 min-h-20`} value={question.prompt || ""} onChange={(event) => onChange({ prompt: event.target.value })} />
      </label>
      {question.type === "mcq" ? (
        <div className="mt-3 space-y-2">
          {(question.options || []).map((option, index) => (
            <label key={index} className="flex items-center gap-2 text-xs text-mute">
              <input
                type="radio"
                name={`correct-${question.id}`}
                checked={Number(question.correct_index) === index}
                onChange={() => onChange({ correct_index: index })}
              />
              <input
                className={field}
                value={option}
                onChange={(event) => {
                  const options = question.options.slice();
                  options[index] = event.target.value;
                  onChange({ options });
                }}
              />
            </label>
          ))}
        </div>
      ) : null}
      {question.type === "short" ? (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block text-xs text-mute">
            Expected answer
            <input className={`${field} mt-1`} value={question.expected || ""} onChange={(event) => onChange({ expected: event.target.value })} />
          </label>
          <label className="block text-xs text-mute">
            Keywords, comma separated
            <input className={`${field} mt-1`} value={keywords} onChange={(event) => onChange({ keywords: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} />
          </label>
        </div>
      ) : null}
      {question.type === "coding" ? (
        <CodingFields question={question} onChange={onChange} />
      ) : null}
      <label className="mt-3 block text-xs text-mute">
        Explanation, shown only if answers are revealed after submit
        <textarea className={`${field} mt-1 min-h-16`} value={question.explanation || ""} onChange={(event) => onChange({ explanation: event.target.value })} />
      </label>
    </article>
  );
}

function CodingFields({ question, onChange }) {
  function patchCase(which, index, partial) {
    const cases = (question[which] || []).slice();
    cases[index] = { ...cases[index], ...partial };
    onChange({ [which]: cases });
  }
  return (
    <div className="mt-3 space-y-3">
      <label className="block text-xs text-mute">
        Signature
        <input className={`${field} mt-1 font-mono`} value={question.signature || ""} onChange={(event) => onChange({ signature: event.target.value })} />
      </label>
      <label className="block text-xs text-mute">
        Starter code
        <textarea className={`${field} mt-1 min-h-28 font-mono text-xs`} value={question.starter_code || ""} onChange={(event) => onChange({ starter_code: event.target.value })} />
      </label>
      <CaseList label="Visible cases" cases={question.visible_cases || []} onPatch={(index, partial) => patchCase("visible_cases", index, partial)} onAdd={() => onChange({ visible_cases: [...(question.visible_cases || []), { stdin: "", expected: "" }] })} />
      <CaseList label="Hidden cases" cases={question.hidden_cases || []} onPatch={(index, partial) => patchCase("hidden_cases", index, partial)} onAdd={() => onChange({ hidden_cases: [...(question.hidden_cases || []), { stdin: "", expected: "" }] })} />
    </div>
  );
}

function CaseList({ label, cases, onPatch, onAdd }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-mute">{label}</p>
        <button type="button" className="text-xs text-hint hover:underline" onClick={onAdd}>
          Add case
        </button>
      </div>
      {cases.map((item, index) => (
        <div key={index} className="mt-2 grid gap-2 sm:grid-cols-2">
          <textarea className={`${field} min-h-16 font-mono text-xs`} value={item.stdin || ""} placeholder="stdin" onChange={(event) => onPatch(index, { stdin: event.target.value })} />
          <textarea className={`${field} min-h-16 font-mono text-xs`} value={item.expected || ""} placeholder="expected stdout" onChange={(event) => onPatch(index, { expected: event.target.value })} />
        </div>
      ))}
    </div>
  );
}
