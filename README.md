# CodeLens AI

Adaptive RAG assistant for JD-based interview readiness.

VTU final-year project, JSS Academy of Technical Education, 2026.

A student uploads a job description. CodeLens explains each requirement, builds a preparation roadmap, and generates a test from those skills. MCQs are scored in code. Coding answers run in a sandbox. The result is a student profile of weak topics and mistake patterns, and the next step follows the same judgment layer the guidance chat already uses: full explanation, hint, gentle reminder, or a break. Debugging help is part of that guidance.

## Problem statement

Placement preparation usually starts from a job description and a pile of generic questions. A chatbot that always gives the full answer does not notice when a student is seeing a mistake for the second time, or when they have repeated it so often that more explanation will not help. A chatbot that only debugs Python never connects the practice to the role the student is actually applying for.

CodeLens sits between those two. It reads the job description, tests the student against the skills in it, and decides how much help to give from the session history.

## Objectives

1. Turn a job description into a structured list of skills, with a short explanation of each requirement and a roadmap.
2. Generate MCQ and coding questions from those skills, and reuse them when the same skills show up again.
3. Score MCQs by comparison, and run coding answers against test cases in a sandboxed process.
4. Record weak topics and mistake patterns on a student profile.
5. Guide the next step with the existing full / hint / gentle / break judgment, including debugging help when the student is stuck on code.

## Modules

### 1. JD understanding

`POST /jd/upload` accepts the posting as JSON text or as a PDF or text file. `GET /jd/analyse/{jd_id}` returns:

```json
{
  "skills": [
    {"name": "SQL", "level": "intermediate", "explanation": "The role writes queries against a relational database."}
  ],
  "roadmap": [
    {"order": 1, "skill": "SQL", "goal": "Filter and join tables", "practice": "Write three joins"}
  ]
}
```

Text is extracted from the file in plain code. The small model is called only on a cache miss, and the JSON is stored in SQLite under a hash of the text.

### 2. Test and guide

`POST /test/generate` builds a short test from the skills. The answer key and the hidden coding cases stay on the server; the first coding case is returned as a sample.

`POST /run` executes Python in a subprocess with a timeout, a CPU limit, and a memory limit. The child process does not see `GROQ_API_KEY`.

`POST /test/submit` scores the attempt. MCQs are compared in code. Coding answers are checked against their test cases in the sandbox. The larger model is asked to explain failures only. A correct paper does not call a model. Weak topics and mistake patterns are written to `student_profile`, and the guidance text follows the judgment directive.

Debugging is still available. `POST /ask` routes a question to the debug, concept, hint, or web agent, reads the session history, and applies the same four directives. The debug agent is how a student gets unstuck while practising, not a separate product.

## Architecture

```text
JD upload
  -> extract text (PDF or plain text)
  -> SQLite, keyed by content hash
  -> small model, only on a cache miss
  -> { skills, roadmap }

Test
  -> reuse questions when the skill list matches
  -> small model writes MCQs and stdin/stdout coding tasks
  -> submit
       MCQ: compare the selected option
       code: sandbox (timeout, CPU, memory) against test cases
       large model: explain failures only
  -> diagnoser writes student_profile
  -> judgment reads sessions -> full | hint | gentle | break
  -> guide returns the message and the next practice step

Guidance chat
  POST /ask
    -> router (keywords first, small model if the query is ambiguous)
    -> judgment
    -> debug | concept | hint | web
    -> session log
    -> { answer, agent_used, directive }
```

State lives in SQLite (`codelens.db`): sessions, pending knowledge-base items, job descriptions, cached analyses, generated tests, and student profiles. Retrieved debugging notes live in Chroma (`codelens_kb`).

Groq models, both set in `rag_core/llm.py`:

| Use | Model |
| --- | --- |
| Routing, JD parsing, question generation | `openai/gpt-oss-20b` |
| Explanations, including why a test failed | `openai/gpt-oss-120b` |

`llama-3.3-70b-versatile` is retired on Groq's self-serve tiers. Clients are created when the API starts, not when a module is imported. Each agent call logs `agent=... latency_s=...`.

## Judgment

The wire values are lowercase. The rules run in this order:

| Directive | When it is chosen |
| --- | --- |
| `full` | No recent history. Also when the student is already stuck and still needs the whole explanation. |
| `hint` | This error is already in the recent history, and the student is not flagged as stuck. An explicit hint request uses this too. |
| `gentle` | The question continues a topic from the last few sessions. |
| `break` | The same error has already been logged four or more times. Give the answer, and tell the student to rest. |

Stuck means the same error has been logged at least three times, or five turns landed inside ten minutes. Interview skills that are not in the keyword list are passed into the same function, so a repeated SQL miss can come back as `gentle` and a repeated `NameError` can come back as `break`.

## Setup

Python 3.10 or newer.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put the Groq key in `.env`:

```bash
GROQ_API_KEY=your_key_here
```

Then build the local database and the debugging knowledge base, and start the API:

```bash
python -m rag_core.init_db
python -m rag_core.build_kb
uvicorn rag_core.api:app --reload --port 8000
```

Tests mock the model. They do not need a key:

```bash
pytest
```

The React client lives in `frontend/`. See `frontend/README.md`. `student_portal/` is the earlier guidance chat and still talks to `POST /ask`.

## API

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `POST` | `/ask` | `{ "student_id", "query" }` | `{ "answer", "agent_used", "directive" }` |
| `POST` | `/jd/upload` | JSON `{ "text" }` or a multipart file field `file` (PDF or text) | `{ "jd_id" }` |
| `GET` | `/jd/analyse/{jd_id}` | | `{ "skills", "roadmap" }` |
| `POST` | `/test/generate` | `{ "jd_id" }` | `{ "jd_id", "questions" }` |
| `POST` | `/run` | `{ "code", "language" }` | `{ "stdout", "stderr" }` |
| `POST` | `/test/submit` | `{ "student_id", "jd_id", "answers" }` | `{ "score", "weak_topics", "guidance" }` |

`guidance` is `{ "directive", "message", "next_steps", "mistake_patterns" }`. `score` is 0 to 100.

`POST /ask` also accepts `"profile": true` and then includes `response_time` and a per-step `profiling` object. `answers` items are `{ "question_id", "selected" }` for an MCQ and `{ "question_id", "code", "language" }` for a coding question.

Teacher review of web-search notes, before they enter the knowledge base:

| Method | Path |
| --- | --- |
| `GET` | `/pending-kb` |
| `POST` | `/approve-kb/{item_id}` |
| `POST` | `/reject-kb/{item_id}` |
| `GET` | `/sessions` |

## Layout

```text
rag_core/api.py            HTTP contract
rag_core/schemas.py        Pydantic models
rag_core/llm.py            shared Groq clients and model ids
rag_core/judgment.py       full / hint / gentle / break
rag_core/pipeline.py       POST /ask
rag_core/agents/           debug, concept, hint, web, JD, test, diagnosis, guide
rag_core/sandbox/          subprocess runner
knowledge_base/            notes used when a student is debugging
tests/                     judgment, scoring, sandbox, schemas
```

## Team

- Raghava S. Ayyaji
- Arjun
- Nishith J Rao
- Srishant

## Earlier evaluation

RAGAS on the guidance answers, April 2026: answer relevancy 82.98%, faithfulness 47.29%. Those numbers are for the debugging knowledge base, not for the JD modules. An earlier guidance-chat deployment is at http://3.104.106.185/.
