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

Text is extracted from the file in plain code. The small model is called only on a cache miss, and the parsed JSON is stored on the job description in MongoDB under a hash of the text.

### 2. Test and guide

`POST /test/generate` builds a short test from the skills. The answer key and the hidden coding cases stay on the server; the first coding case is returned as a sample.

`POST /run` executes Python in a subprocess with a timeout, a CPU limit, and a memory limit. The editor sends the sample stdin with the code. The child process does not see `GROQ_API_KEY`.

`POST /test/submit` scores the attempt. MCQs are compared in code. Coding answers are checked against their test cases in the sandbox. The larger model is asked to explain failures only. A correct paper does not call a model. Weak topics, mistake patterns, and the score are written to that student's persona, and the guidance text follows the judgment directive.

Debugging is still available. `POST /ask` routes a question to the debug, concept, hint, or web agent, reads the session history, and applies the same four directives. The debug agent is how a student gets unstuck while practising, not a separate product.

## Architecture

```text
JD upload
  -> extract text (PDF or plain text)
  -> MongoDB jds, keyed by content hash
  -> small model, only on a cache miss
  -> { skills, roadmap }

Test
  -> reuse questions when the skill list matches
  -> small model writes MCQs and stdin/stdout coding tasks
  -> submit
       MCQ: compare the selected option
       code: sandbox (timeout, CPU, memory) against test cases
       large model: explain failures only
  -> diagnoser writes the persona and a submission
  -> judgment reads activity -> full | hint | gentle | break
  -> guide returns the message and the next practice step

Guidance chat
  POST /ask
    -> router (keywords first, small model if the query is ambiguous)
    -> judgment reads MongoDB activity
    -> debug | concept | hint | web
    -> activity row, persona note, chat messages
    -> web results stop in kb_pending
    -> { answer, agent_used, directive, chat_id }
```

Application state lives in MongoDB. Retrieved debugging notes live in Chroma (`codelens_kb`). A web result does not enter Chroma until a teacher approves it.

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

Python 3.10 or newer, and Node 18 or newer for the React client. The UI in `frontend/` was built by Arjun. It calls this API through `VITE_API_URL` (default `http://localhost:8000`). Fixture JSON stays behind `VITE_USE_MOCKS`, which is off.

The API creates MongoDB indexes on startup. MongoDB has to be running first (`docker compose up -d`, or a local MongoDB server). `python -m rag_core.build_kb` builds the debugging notes used by `POST /ask`. That command needs `sentence-transformers`, which is listed in `requirements.txt` because `langchain-huggingface` does not install it on its own. JD upload, analysis, and the test do not read that index. Those notes are the project's own seed corpus. Anything a student session proposes waits for a teacher.

On startup the API loads the `all-MiniLM-L6-v2` embedding model and, when the index exists, opens it. That work used to land on the first `POST /ask`. The server log line `embedding model ready` means a guidance question will not wait on the model load.

### Windows (PowerShell)

From the repo root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

If activation is blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in that window, or call `.\venv\Scripts\python.exe` instead of `python` after the venv exists.

Edit `.env` and set the key and a real JWT secret (at least 32 characters):

```text
GROQ_API_KEY=your_key_here
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=codelens
JWT_SECRET=a-long-random-string
```

### MongoDB on Windows

Either of these is enough. The API uses `MONGODB_URI` (default `mongodb://localhost:27017`) and `MONGODB_DB` (default `codelens`).

Docker Desktop, from the repo root:

```powershell
docker compose up -d
```

Or MongoDB Community Server, which installs a Windows service on port 27017:

```powershell
winget install MongoDB.Server
```

`.\start-dev.ps1` checks port 27017 and runs `docker compose up -d` when Docker is available and nothing is listening. Create the first teacher (students register themselves in the client; teachers cannot):

```powershell
python -m rag_core.create_teacher --name "Ada Rao" --email ada@school.edu --password "a long secret"
```

If an older `codelens.db` is still around:

```powershell
python -m rag_core.migrate_sqlite
```

That prints a one-time password for each migrated student id. There is no password-reset route yet.

Build the knowledge base, then start the API:

```powershell
python -m rag_core.build_kb
uvicorn rag_core.api:app --reload --port 8000
```

In a second window, start the client:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. One window for both processes:

```powershell
.\start-dev.ps1
```

### Linux and macOS

From the repo root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set the key and a real JWT secret, same variables as on Windows. Start MongoDB with `docker compose up -d` or a local `mongod` on port 27017. `./start-dev.sh` does the Docker check. Then create a teacher and build the seed knowledge base:

```bash
python -m rag_core.create_teacher --name "Ada Rao" --email ada@school.edu --password "a long secret"
python -m rag_core.build_kb
uvicorn rag_core.api:app --reload --port 8000
```

In a second terminal, start the client:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. One terminal for both processes:

```bash
./start-dev.sh
```

### Tests

The API tests mock the model. They do not need a key:

```bash
pytest
```

The client production build:

```bash
cd frontend && npm install && npm run build
```

`student_portal/` is the earlier guidance chat. It still posts a `student_id` and does not send a bearer token, so it no longer reaches the API. The React client in `frontend/` is the one this backend serves. See `frontend/README.md` and `frontend/API_CONTRACT.md`. Existing screens read `localStorage` key `codelens.token` and send `Authorization: Bearer`. Login, My Space, and the teacher dashboard are built in the frontend branch.

## Database design

Application data is in MongoDB. Chroma (`codelens_kb`, on disk under `chroma_db/`) is only the vector index of debugging notes. The two stores are not joined. A document reaches Chroma from a running server only when a teacher approves a row in `kb_pending`. `python -m rag_core.build_kb` is the offline seed of the project's own notes in `knowledge_base/`.

Configuration is `MONGODB_URI` (default `mongodb://localhost:27017`) and `MONGODB_DB` (default `codelens`). The driver is Motor. `python -m rag_core.init_db` pings the server and prints the indexes. Timestamps are stored as naive UTC and returned as ISO-8601 with a `Z`.

`user_id` on every learning document is the string form of `users._id`. Student routes take that id from the JWT. A `student_id` field in a request body is ignored.

### Collections

| Collection | Document | Indexes |
| --- | --- | --- |
| `users` | `name`, `email` (lowercased), `password_hash` (bcrypt), `role` (`student` or `teacher`), `disabled`, `created_at`. Migrated accounts also have `legacy_student_id`. | unique `email`; `role`; unique sparse `legacy_student_id` |
| `chats` | `user_id`, `title` (first query, trimmed to 80 characters), `messages[]`, `created_at`, `updated_at`. Each message is `{role, content, directive, agent_used, ts}`. User messages store `directive` and `agent_used` as null. | `user_id`; `(user_id, updated_at desc)` |
| `personas` | One document per student. `user_id`, `weak_topics[]`, `mistake_patterns[]`, `scores[{test_id, score, created_at}]`, `jd_ids[]`, `learning_notes[]`, `updated_at`. | unique `user_id` |
| `jds` | `_id` is a uuid hex string. `user_id`, `content_hash`, `filename`, `raw_text`, `analysis` (cached `{skills, roadmap}` or null), `created_at`. | `user_id`; `content_hash` |
| `tests` | `jd_id`, `user_id`, `cache_key` (hash of the skill list), `questions` (includes the answer key), `created_at`. | unique `jd_id`; `cache_key`; `user_id` |
| `submissions` | `user_id`, `jd_id`, `score`, `answers`, `weak_topics`, `mistake_patterns`, `created_at`. `_id` is the `test_id` returned by history. | `(user_id, created_at desc)` |
| `kb_pending` | `content`, `title`, `topic`, `tags`, `difficulty`, `type`, `origin`, `source`, `proposed_by`, `proposer_name`, `proposer_role`, `query`, `status` (`pending`, `approved`, or `rejected`), `reject_reason`, `reviewed_by`, `reviewed_at`, `created_at`, `updated_at`, `chroma_ids`. Migrated rows may have `legacy_id`. | `status`; `(status, created_at)`; `(status, updated_at desc)`; `created_at`; `topic`; `type`; `source`; `tags`; unique sparse `legacy_id` |
| `kb_uploads` | `filename`, `media_type`, `size`, `status` (`chunked` or `failed`), `progress`, `error`, `chunks`, `kb_item_id`, `uploaded_by`, `created_at`. | `created_at desc`; `status`; `uploaded_by`; `kb_item_id` |
| `activity` | `user_id`, `type`, `detail`, `ts`. | `(user_id, ts desc)`; `(ts desc)`; `(user_id, type, ts desc)` |

### How the persona stays current

A chat turn calls `note_chat`, which upserts the persona and appends a learning note (`$slice` keeps the last 100). Uploading a job description calls `remember_jd` and `$addToSet`s `jd_ids`. Submitting a test calls `apply_attempt`: `weak_topics` and `mistake_patterns` are replaced with that attempt, the score is pushed (last 200 kept), and the job description is added to `jd_ids`. `GET /me/persona` hydrates `jd_ids` into `{jd_id, filename, created_at}` and returns that list as `jds`. `GET /me/history` reads job descriptions and submissions directly. `persona.scores` is a denormalized copy of those submissions.

### Judgment history

`get_student_context` reads `activity` documents whose `type` is `ask` or `test_submit`, newer than the lookback window (30 minutes), newest first. Chat messages are not the judgment source. The activity `detail` carries `topic`, `error_type`, and `directive`, so a topic that is not in the query text still counts. The rules are unchanged: stuck at three of the same error or five turns inside ten minutes; `break` at four of the same error.

Other activity types, recorded for the teacher feed and not read by judgment: `register`, `login`, `jd_upload`, `jd_analyse`, `test_generate`, `run` (language and code length only), `account` (disable or reset).

### Knowledge-base gate

`stage_for_approval` inserts a `kb_pending` document with `status: pending` and `origin: ai`. The web agent uses only that function. `write_kb_document` runs when a teacher approves a pending note, creates a note with `approve` left on (the default), bulk-approves, or accepts upload chunks. It writes the Chroma index in `CODELENS_KB` (`codelens_kb`). If Chroma raises, a single approve or create stays `pending` and the API returns 502. A bulk id that fails is listed in `failed` and stays `pending`. Deleting an approved note removes its Chroma vectors first. Editing a pending row and rejecting a row do not write to Chroma. Editing an approved note's title, content, or source replaces its vectors. A second approve or reject returns 409.

### Relationships

```text
users 1──* chats
users 1──1 personas
users 1──* jds 1──1 tests
users 1──* submissions
users 1──* activity
users 1──* kb_pending   (proposed_by / reviewed_by)
users 1──* kb_uploads   (uploaded_by; kb_item_id points at kb_pending)
```

`POST /teacher/students/{id}/reset` deletes that student's chats, persona, submissions, activity, job descriptions, and tests, then writes one `account` activity `{action: reset, by}`. The user document and any `kb_pending` rows they proposed stay.

### Sample documents

```json
{
  "users": {
    "name": "Meera",
    "email": "meera@college.edu",
    "password_hash": "$2b$12$...",
    "role": "student",
    "disabled": false,
    "created_at": "2026-10-21T05:00:00"
  },
  "personas": {
    "user_id": "6716...",
    "weak_topics": ["SQL"],
    "mistake_patterns": ["missing WHERE"],
    "scores": [{"test_id": "6717...", "score": 50, "created_at": "2026-10-21T05:10:00"}],
    "jd_ids": ["a1b2c3..."],
    "learning_notes": ["score 50.0 weak SQL"],
    "updated_at": "2026-10-21T05:10:00"
  },
  "activity": {
    "user_id": "6716...",
    "type": "test_submit",
    "detail": {"jd_id": "a1b2c3...", "score": 50, "topic": "SQL", "error_type": "missing WHERE", "directive": "full"},
    "ts": "2026-10-21T05:10:00"
  }
}
```

### Migrating an old SQLite file

`python -m rag_core.migrate_sqlite` reads `codelens.db` (or `--sqlite PATH`). Each legacy `student_id` becomes a user with `legacy_student_id`, email `{slug}@migrated.codelens.local`, and a random password printed once. Sessions become one chat titled "Migrated history" plus `ask` activity. Profiles become personas. Job descriptions are assigned to the first profile that names them. Knowledge-base rows keep their status and `legacy_id`. Approved rows are not written to Chroma again. Running the script twice skips users that already have that `legacy_student_id`.

## API

Every route except `GET /`, `GET /health`, `POST /auth/register`, and `POST /auth/login` requires `Authorization: Bearer <token>`. The token is HS256, lasts 7 days, and carries `sub` and `role`. Role and the disabled flag are loaded from MongoDB on each request. A disabled account gets 403. Register always creates a student. A body that asks for `role: teacher` is 403. Teachers are created with `python -m rag_core.create_teacher`.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | `{ "name", "email", "password" }` | `{ "token", "user": { "id", "name", "email", "role" } }` |
| `POST` | `/auth/login` | `{ "email", "password" }` | same as register |
| `GET` | `/auth/me` | | `{ "id", "name", "email", "role" }` |
| `POST` | `/ask` | `{ "query", "chat_id"? }` | `{ "answer", "agent_used", "directive", "chat_id" }` |
| `GET` | `/me/chats` | | `[{ "chat_id", "title", "updated_at" }]` |
| `GET` | `/me/chats/{chat_id}` | | `{ "chat_id", "title", "messages" }` |
| `GET` | `/me/persona` | | `{ "weak_topics", "mistake_patterns", "scores", "jds" }` |
| `GET` | `/me/history` | | `{ "jds": [...], "tests": [{ "test_id", "score", "created_at" }] }` |
| `POST` | `/jd/upload` | JSON `{ "text" }` or multipart `file` | `{ "jd_id" }` |
| `GET` | `/jd/analyse/{jd_id}` | | `{ "skills", "roadmap" }` |
| `POST` | `/test/generate` | `{ "jd_id" }` | `{ "jd_id", "questions" }` |
| `POST` | `/run` | `{ "code", "language", "stdin"? }` | `{ "stdout", "stderr" }` |
| `POST` | `/test/submit` | `{ "jd_id", "answers" }` | `{ "score", "weak_topics", "guidance" }` |

`guidance` is `{ "directive", "message", "next_steps", "mistake_patterns" }`. `score` is 0 to 100. `answers` items are `{ "question_id", "selected" }` for an MCQ and `{ "question_id", "code", "language" }` for a coding question. A missing `chat_id` creates a chat. Another student's job description or chat is 404.

Teacher routes. A student token receives 403.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/teacher/overview` | | `{ "total_students", "active_today", "avg_score", "directive_counts", "pending_kb" }` |
| `GET` | `/teacher/students` | | `[{ "id", "name", "email", "disabled", "last_active", "avg_score", "weak_topics" }]` |
| `GET` | `/teacher/students/{id}` | | `{ "user", "persona", "recent_activity", "tests" }` |
| `GET` | `/teacher/students/{id}/chats` | | same shape as `/me/chats` |
| `GET` | `/teacher/students/{id}/chats/{chat_id}` | | same shape as `/me/chats/{chat_id}` |
| `PATCH` | `/teacher/students/{id}` | `{ "disabled" }` | student summary |
| `POST` | `/teacher/students/{id}/reset` | | `{ "id", "reset": true }` |
| `GET` | `/teacher/activity?limit=` | `limit` 1–200, default 50 | activity feed |
| `GET` | `/teacher/kb` | filters `q`, `status`, `topic`, `tag`, `type`, `source`, `from`, `to`, `page`, `page_size` | `{ "items", "total", "page", "page_size", "counts", "facets" }` |
| `POST` | `/teacher/kb` | `{ "title", "content", "topic", "tags", "difficulty", "source", "type", "approve"? }` | the item. `approve` defaults to true and writes Chroma |
| `GET` | `/teacher/kb/pending` | | pending items |
| `GET` | `/teacher/kb/{id}` | | the item |
| `PUT` | `/teacher/kb/{id}` | any of `title`, `content`, `topic`, `tags`, `difficulty`, `source`, `type` | the edited item. Status does not change |
| `DELETE` | `/teacher/kb/{id}` | | `{ "id", "deleted": true }`. Approved rows are removed from Chroma |
| `POST` | `/teacher/kb/{id}/approve` | | approved item; this writes Chroma |
| `POST` | `/teacher/kb/{id}/reject` | `{ "reason"? }` | rejected item |
| `POST` | `/teacher/kb/bulk` | `{ "ids", "action", "reason"? }` | `{ "updated", "failed" }` |
| `GET` | `/teacher/kb/uploads` | | upload records, newest first |
| `POST` | `/teacher/kb/uploads` | multipart `file` | the upload record |
| `POST` | `/teacher/kb/uploads/{id}/approve` | `{ "chunk_indexes"?, "title"?, "topic"?, "tags"?, "difficulty"? }` | `{ "upload", "item" }` |
| `DELETE` | `/teacher/kb/uploads/{id}` | | `{ "id", "deleted": true }` |

`directive_counts` is `{ "full", "hint", "gentle", "break" }`. `avg_score` on the overview is the mean of every submission, `0.0` when there are none. A student's `avg_score` is `null` when they have no submissions. `active_today` counts distinct students with any activity since UTC midnight.

`/approve-kb`, `/reject-kb`, `/pending-kb`, and `/sessions` are not registered.

## Layout

```text
rag_core/api.py            HTTP contract
rag_core/schemas.py        Pydantic models
rag_core/auth.py           bcrypt and JWT
rag_core/mongo.py          Motor client and indexes
rag_core/store.py          collection access
rag_core/create_teacher.py teacher seed CLI
rag_core/migrate_sqlite.py SQLite to MongoDB
rag_core/llm.py            shared Groq clients and model ids
rag_core/judgment.py       full / hint / gentle / break
rag_core/pipeline.py       POST /ask
rag_core/kb_update.py      pending queue and the Chroma write
rag_core/agents/           debug, concept, hint, web, JD, test, diagnosis, guide
rag_core/sandbox/          subprocess runner
knowledge_base/            notes used when a student is debugging
docker-compose.yml         MongoDB 7.0 on port 27017
deploy/simple/             Vercel + two EC2 instances (beginner deploy)
tests/                     auth, judgment, scoring, sandbox, schemas
```

## AWS

The beginner path puts the React app on Vercel and runs the API and MongoDB as two EC2 instances in the default Mumbai VPC. The console clicks and the two setup commands are in [docs/DEPLOY_SIMPLE.md](docs/DEPLOY_SIMPLE.md).

A three-server layout in a custom VPC (Nginx, the API, and a private database) is the advanced option. That guide, the security-group table, and the teardown are in [docs/DEPLOY_AWS.md](docs/DEPLOY_AWS.md).

## Team

- Raghava S. Ayyaji
- Arjun
- Nishith J Rao
- Srishant

## Earlier evaluation

RAGAS on the guidance answers, April 2026: answer relevancy 82.98%, faithfulness 47.29%. Those numbers are for the debugging knowledge base, not for the JD modules. An earlier guidance-chat deployment is at http://3.104.106.185/.
