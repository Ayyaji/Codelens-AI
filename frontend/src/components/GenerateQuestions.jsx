import { useState } from "react";
import { generateClassQuestions } from "../api/client";
import { btn, field } from "./ui";

const MCQ_BATCH = 3;
const CODE_BATCH = 1;
const BUSY = "AI service is busy, please try again in a few seconds.";

async function generateInChunks(body) {
  let mcqLeft = Number(body.mcq_count) || 0;
  let codeLeft = Number(body.coding_count) || 0;
  const questions = [];
  const flagged = [];
  const warnings = [];
  const avoid = [...(body.avoid || [])];
  let busyMessage = "";
  while (mcqLeft > 0 || codeLeft > 0) {
    const mcqCount = Math.min(MCQ_BATCH, mcqLeft);
    const codingCount = mcqCount > 0 ? 0 : Math.min(CODE_BATCH, codeLeft);
    let data;
    try {
      data = await generateClassQuestions({
        ...body,
        mcq_count: mcqCount,
        coding_count: codingCount,
        avoid,
      });
    } catch (err) {
      if (err.status === 503) {
        busyMessage = err.message || BUSY;
        break;
      }
      throw err;
    }
    const made = Array.isArray(data?.questions) ? data.questions : [];
    questions.push(...made);
    flagged.push(...(Array.isArray(data?.flagged) ? data.flagged : []));
    warnings.push(...(Array.isArray(data?.warnings) ? data.warnings : []));
    for (const question of made) avoid.push(String(question.prompt || "").slice(0, 300));
    if (data?.busy) {
      busyMessage = BUSY;
      break;
    }
    if (mcqCount > 0) {
      mcqLeft -= mcqCount;
      if (!made.length) mcqLeft = 0;
    } else {
      codeLeft -= codingCount;
    }
  }
  return { questions, flagged, warnings, busyMessage };
}

export function GenerateQuestions({ testType, topic, locked, onAdd, onSettings }) {
  const [syllabus, setSyllabus] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [mcqCount, setMcqCount] = useState(testType === "coding" ? 0 : 3);
  const [codingCount, setCodingCount] = useState(testType === "mcq" ? 0 : 1);
  const [useKb, setUseKb] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const mcqAllowed = testType !== "coding";
  const codingAllowed = testType !== "mcq";
  const asked = (mcqAllowed ? Number(mcqCount) || 0 : 0) + (codingAllowed ? Number(codingCount) || 0 : 0);

  function publishSettings(partial = {}) {
    onSettings?.({
      syllabus: syllabus.trim(),
      difficulty,
      useKb,
      topic: topic || "",
      ...partial,
    });
  }

  async function generate() {
    setGenerating(true);
    setError("");
    setNotice("");
    try {
      const nextSyllabus = syllabus.trim() || topic || "general";
      publishSettings({ syllabus: nextSyllabus });
      const result = await generateInChunks({
        syllabus: nextSyllabus,
        topic: topic || "",
        difficulty,
        mcq_count: mcqAllowed ? Number(mcqCount) || 0 : 0,
        coding_count: codingAllowed ? Number(codingCount) || 0 : 0,
        language: "python",
        use_kb: useKb,
      });
      if (result.questions.length) {
        onAdd(result.questions.map((question) => ({ ...question, generated: true })));
      }
      const notes = [];
      if (result.warnings.length) notes.push(...result.warnings);
      if (result.flagged.length) {
        notes.push(
          result.flagged
            .map((item) => `${item.type === "coding" ? "Coding" : "MCQ"} dropped: ${item.reason || "validation failed"}`)
            .join(" "),
        );
      }
      if (!result.questions.length && !result.busyMessage) {
        notes.push("Nothing usable came back. Adjust the syllabus and try again.");
      }
      if (result.questions.length) notes.push("These are drafts. Review them, then save. Nothing is published yet.");
      setNotice(notes.filter(Boolean).join(" "));
      if (result.busyMessage) setError(result.questions.length ? `${result.busyMessage} The questions above were kept.` : result.busyMessage);
    } catch (err) {
      setError(err.message || "Could not generate questions.");
    } finally {
      setGenerating(false);
    }
  }

  if (locked) return null;

  return (
    <section className="mt-8 rounded-xl border border-line bg-panel p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Generate with AI</h2>
          <p className="mt-1 text-sm text-mute">
            Drafts land in the editor for you to edit or remove. Publishing is a separate save.
          </p>
        </div>
      </div>
      {error ? (
        <p role="alert" className="mt-3 rounded-lg border border-break/40 bg-break/10 px-3 py-2 text-sm text-[#f3c1c7]">
          {error}
        </p>
      ) : null}
      {notice ? <p className="mt-3 text-sm text-mute">{notice}</p> : null}
      <label className="mt-3 block text-xs text-mute">
        Topics or syllabus
        <textarea
          className={`${field} mt-1 min-h-24`}
          value={syllabus}
          onChange={(event) => {
            setSyllabus(event.target.value);
            publishSettings({ syllabus: event.target.value.trim() });
          }}
          placeholder="Binary search, hash maps, and ACID. First-year level."
        />
      </label>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block text-xs text-mute">
          Difficulty
          <select
            className={`${field} mt-1`}
            value={difficulty}
            onChange={(event) => {
              setDifficulty(event.target.value);
              publishSettings({ difficulty: event.target.value });
            }}
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
        <label className="block text-xs text-mute">
          MCQs
          <input
            className={`${field} mt-1`}
            type="number"
            min="0"
            max="8"
            disabled={!mcqAllowed}
            value={mcqAllowed ? mcqCount : 0}
            onChange={(event) => setMcqCount(event.target.value)}
          />
        </label>
        <label className="block text-xs text-mute">
          Coding problems
          <input
            className={`${field} mt-1`}
            type="number"
            min="0"
            max="4"
            disabled={!codingAllowed}
            value={codingAllowed ? codingCount : 0}
            onChange={(event) => setCodingCount(event.target.value)}
          />
        </label>
        <label className="block text-xs text-mute">
          Language
          <select className={`${field} mt-1`} value="python" disabled>
            <option value="python">Python</option>
          </select>
        </label>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm text-mute">
          <input
            type="checkbox"
            checked={useKb}
            onChange={(event) => {
              setUseKb(event.target.checked);
              publishSettings({ useKb: event.target.checked });
            }}
          />
          Ground on the approved knowledge base
        </label>
        <button type="button" className={btn} onClick={generate} disabled={generating || asked < 1 || !syllabus.trim()}>
          {generating ? "Generating…" : "Generate drafts"}
        </button>
      </div>
      <p className="mt-2 text-xs text-faint">Requests go out a few questions at a time so a busy Groq key does not drop the whole set.</p>
    </section>
  );
}
