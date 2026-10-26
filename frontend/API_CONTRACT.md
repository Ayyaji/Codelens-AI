# CodeLens API contract (frontend)

The React client calls the FastAPI app. Paths and JSON below follow `rag_core/schemas.py` and `rag_core/api.py` on the MongoDB auth branch (PR #3, `cursor/mongodb-auth-backend-3267`). Where this UI computes something the API does not send, or where PR #3's client and this one disagree, that is called out.

Base URL: `VITE_API_URL` (no path prefix, no trailing slash). When the variable is missing the client uses `http://localhost:8000`. The browser sends requests directly. CORS allows the Vite dev origin (`http://localhost:5173` and `http://127.0.0.1:5173`, plus the preview port 4173) and any other origin. Send the access token as a header, not a cookie:

```http
Authorization: Bearer <token>
```

`src/api/client.js` reads that token from `localStorage` key `codelens.token` (`TOKEN_STORAGE_KEY`). `getToken` and `setToken` are the accessors. `registerAccount` and `loginAccount` store it. Logout clears it. The signed-in user (`id`, `name`, `email`, `role`) lives in the same React session as the in-progress test. A refresh calls `GET /auth/me` and puts that user back. The old student-id field is gone.

Errors are FastAPI's `{"detail": "<message>"}`. `detail` may be a string or a validation list. The client surfaces it as text. Statuses in use include 400, 401 (missing or bad token, or a wrong login), 403 (disabled account, a student calling a teacher route, or a teacher trying to self-register), 404, 409 (duplicate email, or a knowledge-base item that is no longer pending), 413, 422, and 502.

Every route except `POST /auth/register` and `POST /auth/login` requires the bearer token. The server uses the token's user. A `student_id` in the body is ignored. Teachers cannot self-register.

A 401 on any route other than login or register clears the token and returns to `/login`. A 403 whose message says the account is disabled does the same. A 403 `Teacher access required` does not.

`src/mocks/` answers a call when `VITE_USE_MOCKS=true`, or when its name appears in `VITE_MOCK_ENDPOINTS`. The committed default is `VITE_USE_MOCKS=false`. With the flag on, `POST /ask` is mocked too, so My Space and the dashboard work with no API. Names: `upload`, `analyse`, `generate`, `submit`, `run`, `auth`, `ask`, `chats`, `persona`, `history`, `overview`, `students`, `activity`, `kb`.

Directive values on the wire are lowercase: `full`, `hint`, `gentle`, `break`. The UI prints them as FULL / HINT / GENTLE / BREAK.

The old open routes `GET /pending-kb`, `POST /approve-kb/{id}`, `POST /reject-kb/{id}`, and `GET /sessions` are not registered.

## Mismatches

Checked against PR #3. This client follows the shapes in that branch. These are the places a reader of the short path list, or of PR #3's frontend diff, can be surprised.

1. PR #3's `client.js` never mocks `POST /ask`. This one does when `VITE_USE_MOCKS=true` or `ask` is listed, so the guidance chat works offline. With the flag off, `/ask` is live. The body is `{ "query", "chat_id"? }`. `student_id` is not sent. The API ignores it if a client still sends it. `profile` is no longer a public flag.
2. `GET /auth/me` returns `{id, name, email, role}` and does not include `disabled`. A disabled token fails earlier with 403 `Account disabled`.
3. Registering an email that already exists is 409 `Email is already registered`. A password outside 8–72 characters is 422. FastAPI sends `detail` as a list, and Pydantic prefixes the validator text with `Value error, `. The client strips that prefix and shows `Password must be 8 to 72 characters.` Login does not use that length rule: a wrong password is 401 `Invalid email or password`, including when the account is disabled and the password is also wrong. Disabled plus the right password is 403 `Account disabled`.
4. `{"role": "teacher"}` on register is 403 `Teachers cannot self-register`. The form does not send `role`.
5. Search on the students table is done in the browser. `GET /teacher/students` has no query parameter.
6. `GET /teacher/activity` items include `name` and `email`. `recent_activity` inside `GET /teacher/students/{id}` does not, because the backend only joins users for the feed. The UI treats both fields as optional.
7. `GET /teacher/students/{id}/chats/{chat_id}` exists on PR #3 and is used to read a transcript. It was not in the short path list. The body is the same chat object as `GET /me/chats/{chat_id}`.
8. History tests and persona scores are `{test_id, score, created_at}` only. Per-attempt weak topics are not on that object. Persona `weak_topics` and `mistake_patterns` are the latest submission.
9. `directive_counts.break` is the JSON key. `break_` is only the Python attribute name, because `break` is a keyword. The client also accepts `break_` if a serializer ever emits it.
10. Overview `avg_score` is `0` when nobody has submitted. A student's `avg_score` is `null` in that case. `active_today` counts distinct students with any activity since UTC midnight.
11. Reset returns `{id, reset: true}`. It deletes chats, the persona, submissions, activity, job descriptions, and generated tests. The account and the disabled flag stay. Knowledge-base items they proposed stay in the queue. The mock has no generated-test collection separate from submissions.
12. Real chat, user, submission, and knowledge-base ids are Mongo ObjectId strings. Job description ids are uuid hex. The client treats every id as an opaque string. The mock uses readable ids such as `stu_ada` and `chat_ada_none`.
13. The library page calls the proposed `/teacher/kb` collection, upload, and bulk routes documented at the end of the teacher section. PR #3 only has `GET /teacher/kb/pending`, `PUT` of `{content}` while pending, and approve/reject with no reason. Those four still exist in the mock. The new page does not use the content-only edit.

---

## POST /auth/register

Mock name: `auth`.

```json
{ "name": "Ada", "email": "ada@school.edu", "password": "at least 8 characters" }
```

`name` is trimmed, at most 80 characters. `email` is lowercased. `password` must be 8 to 72 characters. Response:

```json
{ "token": "<jwt>", "user": { "id": "<object id>", "name": "Ada", "email": "ada@school.edu", "role": "student" } }
```

The new user is always a student.

## POST /auth/login

Mock name: `auth`.

```json
{ "email": "ada@school.edu", "password": "at least 8 characters" }
```

Same response shape as register.

## GET /auth/me

Mock name: `auth`.

Returns the user object `{id, name, email, role}`.

---

## POST /ask

Mock name: `ask`. Mocked only when the flag is on. Requires the bearer token.

Request:

```json
{ "query": "Why does this raise TypeError?", "chat_id": "optional existing chat" }
```

Omit `chat_id` to open a chat. The function signature is `ask({ query, chatId })`. A `chat_id` owned by someone else is 404 `Chat not found`.

Response:

```json
{
  "answer": "None has no subscript.",
  "agent_used": "debug",
  "directive": "hint",
  "chat_id": "66f0..."
}
```

`student_id`, `query`, `response_time`, and `profiling` are ignored if the API still sends them.

## GET /me/chats

Mock name: `chats`.

```json
[{ "chat_id": "66f0...", "title": "Why does this raise TypeError?", "updated_at": "2026-10-21T05:00:00Z" }]
```

Newest first. The array is the body. There is no wrapper object.

## GET /me/chats/{chat_id}

Mock name: `chats`.

```json
{
  "chat_id": "66f0...",
  "title": "Why does this raise TypeError?",
  "messages": [
    { "role": "user", "content": "Why does this raise TypeError?", "directive": null, "agent_used": null, "ts": "2026-10-21T05:00:00Z" },
    { "role": "assistant", "content": "None has no subscript.", "directive": "hint", "agent_used": "debug", "ts": "2026-10-21T05:00:00Z" }
  ]
}
```

A user message has `directive` and `agent_used` set to null.

## GET /me/persona

Mock name: `persona`.

```json
{
  "weak_topics": ["SQL"],
  "mistake_patterns": ["concept_gap:SQL"],
  "scores": [{ "test_id": "66f1...", "score": 66.7, "created_at": "2026-10-21T05:00:00Z" }],
  "jds": [{ "jd_id": "abc", "filename": "jd.txt", "created_at": "2026-10-21T05:00:00Z" }]
}
```

Empty lists when the student has no persona yet. `weak_topics` and `mistake_patterns` are the latest submission. `scores` is the attempt history kept on the persona, oldest first.

## GET /me/history

Mock name: `history`.

```json
{
  "jds": [{ "jd_id": "abc", "filename": "jd.txt", "created_at": "2026-10-21T05:00:00Z" }],
  "tests": [{ "test_id": "66f1...", "score": 66.7, "created_at": "2026-10-21T05:00:00Z" }]
}
```

`tests` are scored attempts (submission ids), newest first. `jds` are the job descriptions this student uploaded, newest first. The persona's `jds` follow `jd_ids` order instead.

---

---

## POST /jd/upload

Mock name: `upload`.

Either JSON or multipart.

JSON, used for the paste box:

```json
{ "text": "We are hiring...", "filename": "jd.txt" }
```

The API also accepts `content` instead of `text`. The client sends `text`.

Multipart, used for a file: one field named `file`. PDF or plain text. Limit 2 MB, matching the API.

Response:

```json
{ "jd_id": "jd_mock_8f3a1c" }
```

`jd_id` is an opaque string. The real API uses a uuid hex.

---

## GET /jd/analyse/{jd_id}

Mock name: `analyse`.

Response:

```json
{
  "skills": [
    {
      "name": "SQL",
      "level": "intermediate",
      "explanation": "The role queries a relational database."
    }
  ],
  "roadmap": [
    {
      "order": 1,
      "skill": "SQL",
      "goal": "Filter and join two tables",
      "practice": "Write three joins"
    }
  ]
}
```

`level` is `beginner`, `intermediate`, or `advanced`.

Roadmap items are `{ order: number, skill: string, goal: string, practice: string }`. The UI sorts by `order`.

### Match meter (not an API field)

`GET /jd/analyse/{jd_id}` does not return a match score. The meter is computed in the browser as the average of per-skill weights:

| level | weight |
| --- | --- |
| beginner | 84 |
| intermediate | 62 |
| advanced | 38 |
| anything else | 62 |

Rounded to an integer 0–100. It estimates how approachable the posting is. It is not a student-to-role score. If the API later adds a numeric field, the meter should use that instead of this average.

---

## POST /test/generate

Mock name: `generate`.

Request:

```json
{ "jd_id": "jd_mock_8f3a1c" }
```

Response. The answer key and hidden tests stay on the server. This is `QuestionPublic`:

```json
{
  "jd_id": "jd_mock_8f3a1c",
  "questions": [
    {
      "id": "q1",
      "type": "mcq",
      "skill": "SQL",
      "prompt": "Which clause filters after a join?",
      "options": ["WHERE", "ORDER BY", "GROUP BY", "LIMIT"]
    },
    {
      "id": "c1",
      "type": "coding",
      "skill": "Python",
      "prompt": "Read one integer from stdin and print its double.",
      "language": "python",
      "starter_code": "print(int(input()) * 2)\n",
      "sample_input": "2",
      "sample_output": "4"
    }
  ]
}
```

`type` is `mcq` or `coding`. MCQ items include `options` (two or more strings) and omit the answer. Coding items include `language` (the sandbox runs Python), `starter_code`, and the first case as `sample_input` / `sample_output`. Null fields are omitted (`exclude_none`).

The UI assumes a short test: several MCQs and one or more coding questions. The timer is 20 minutes and is client-only. It is not in this payload.

---

## POST /run

Mock name: `run`.

Request. `stdin` is the sample shown next to the editor. It may be omitted; the server then uses an empty string. A trailing newline is kept.

```json
{ "code": "print(int(input()) * 2)\n", "language": "python", "stdin": "2\n" }
```

Response. Only these two fields:

```json
{ "stdout": "4\n", "stderr": "" }
```

The mock returns a fixed `stdout` of `4\n` for Python so the terminal has something to show. The real sandbox runs the code and feeds `stdin` to the process. Non-Python languages come back as an empty stdout and a stderr message. The client prints stdout as-is and stderr in red. Submit still does not send stdin: hidden cases stay on the server.

---

## POST /test/submit

Mock name: `submit`.

Request:

```json
{
  "jd_id": "jd_mock_8f3a1c",
  "answers": [
    { "question_id": "q1", "selected": "WHERE" },
    { "question_id": "c1", "code": "print(int(input()) * 2)\n", "language": "python" }
  ]
}
```

MCQ answers send `selected` (the option text, or `null` if skipped). Coding answers send `code` and `language`. At least one answer is required.

Response:

```json
{
  "score": 66.7,
  "weak_topics": ["SQL", "Testing"],
  "guidance": {
    "directive": "hint",
    "message": "You have run into SQL before. ...",
    "next_steps": ["SQL: Write three joins"],
    "mistake_patterns": ["concept_gap:SQL", "wrong_output:Testing"]
  }
}
```

`score` is a number from 0 to 100.

`weak_topics` is an ordered list of skill-name strings. The diagnoser lists a skill once, first miss first. It does not send counts.

### Weak-topic chart (derived)

Recharts plots one bar per name. Bar length is rank: the first topic gets `n`, the next `n - 1`, down to 1. The axis is labelled priority. If the API later sends `{ "topic": "SQL", "count": 2 }`, the chart should plot `count` instead.

### Mistakes (derived from strings)

`guidance.mistake_patterns` is a list of strings. The diagnoser builds each one as `"{mistake}:{skill}"`. Known mistake tokens from the evaluator include `concept_gap`, `unanswered`, `wrong_output`, `timeout`, `runtime_error`, `unsupported_language`, and Python exception names such as `NameError`.

The results page splits on the first colon, shows the mistake with underscores as spaces, and shows the skill beside it. A string with no colon is shown whole.

`guidance.message` and `guidance.next_steps` are shown next to the score. `guidance.directive` uses the same badge as the chat.

A client-supplied `student_id` is ignored. The attempt is stored for the token's user. `submitTest({ jdId, answers })` does not send one. The mock also appends the score onto the signed-in student's persona so My Space shows the attempt.

---

## Teacher routes

All of these are 403 `Teacher access required` for a student. Mock names: `overview`, `students`, `activity`, `kb`. Student chats on the detail page use `students`.

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/teacher/overview` | | `{total_students, active_today, avg_score, directive_counts, pending_kb}` |
| `GET` | `/teacher/students` | | `[{id, name, email, disabled, last_active, avg_score, weak_topics}]` |
| `GET` | `/teacher/students/{id}` | | `{user, persona, recent_activity, tests}` |
| `GET` | `/teacher/students/{id}/chats` | | same list as `GET /me/chats` |
| `GET` | `/teacher/students/{id}/chats/{chat_id}` | | same object as `GET /me/chats/{chat_id}` |
| `PATCH` | `/teacher/students/{id}` | `{disabled: true}` | the student list item |
| `POST` | `/teacher/students/{id}/reset` | | `{id, reset: true}` |
| `GET` | `/teacher/activity?limit=` | | newest student events, `limit` 1–200, default 50 |
| `GET` | `/teacher/kb/pending` | | pending notes, oldest first. Still implemented. The library page uses `GET /teacher/kb` below. |
| `PUT` | `/teacher/kb/{id}` | `{content}` on PR #3 | the edited note. This client sends the fuller body in the proposal section. |
| `POST` | `/teacher/kb/{id}/approve` | | the note, `status: "approved"`. On PR #3 this is the only call that writes the note to Chroma |
| `POST` | `/teacher/kb/{id}/reject` | `{reason}` optional on the proposal | the note, `status: "rejected"` |

`directive_counts` is `{full, hint, gentle, break}`.

`user` on the detail is `{id, name, email, role, disabled, created_at}`. `persona` on the detail adds `learning_notes` and `updated_at` to the student persona. `tests` matches history tests. `recent_activity` is the last 20 events for that student.

An activity item is `{id, user_id, type, detail, ts}`. The feed also sends `name` and `email`. `detail` is an object. Guidance rows carry `query`, `agent_used`, `response_time`, `error_type`, `topic`, and `directive`. A test submission adds `score`, `jd_id`, and `test_id`. An account row is `{action, by}` where `action` is `disabled`, `enabled`, or `reset`.

A note on PR #3 is `{id, content, source, proposed_by, status, query, reviewed_by, reviewed_at, created_at}`. `status` is `pending`, `approved`, or `rejected`. Approving or rejecting a note that is not pending is 409. On PR #3, editing a note that is not pending is 409 `Only a pending item can be edited`, and the body is `{content}` only. Blank content is 422. Editing and rejecting do not write to Chroma. The library UI does not call that narrow edit. It calls the proposal below, including while a note is already approved.

The dashboard charts plot `directive_counts` and each student's `avg_score`. Those charts are not extra API fields. The students search box filters the array already returned. `pending_kb` on the overview is still the count of notes with `status: "pending"`.

## Proposed knowledge-base routes

Not on PR #3. The teacher library calls these paths on `VITE_API_URL`. With `VITE_USE_MOCKS=true` (or the `kb` mock name) the fixtures implement them. Against the current auth backend they will 404 until Raghava adds them.

A knowledge item:

```json
{
  "id": "kb_arrays",
  "title": "Arrays: index arithmetic",
  "content": "Markdown body",
  "topic": "Arrays",
  "tags": ["arrays", "dsa"],
  "difficulty": "easy",
  "source": "textbook",
  "type": "concept",
  "origin": "teacher",
  "status": "approved",
  "proposed_by": "tch_rao",
  "proposer_name": "Meera Rao",
  "proposer_role": "teacher",
  "query": "Arrays: index arithmetic",
  "reviewed_by": "tch_rao",
  "reviewed_at": "2026-10-21T05:00:00Z",
  "reject_reason": null,
  "created_at": "2026-10-21T05:00:00Z",
  "updated_at": "2026-10-21T05:00:00Z"
}
```

`difficulty` is `easy`, `medium`, `hard`, or null. `source` is `teacher`, `student`, `ai`, `web`, `upload`, or `textbook`. `type` is `concept`, `qa`, `college`, or `document`. `origin` is who created the row: `teacher`, `student`, `ai`, or `upload`. `status` is `pending`, `approved`, or `rejected`.

`POST /teacher/kb` is teacher-only. The server sets `origin` from the caller. `approve` defaults to true for a teacher, which stores the item as `approved`. `approve: false` leaves it `pending`. An item whose origin is `student` or `ai` stays `pending` even if `approve` is sent. There is no student write route in this client yet.

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/teacher/kb` | | a page, below |
| `POST` | `/teacher/kb` | `{title, content, topic, tags, difficulty, source, type, approve?}` | the item |
| `GET` | `/teacher/kb/{id}` | | the item |
| `PUT` | `/teacher/kb/{id}` | any of `title`, `content`, `topic`, `tags`, `difficulty`, `source`, `type` | the item. Pending and approved rows can be edited. Status does not change. |
| `DELETE` | `/teacher/kb/{id}` | | `{id, deleted: true}` |
| `POST` | `/teacher/kb/bulk` | `{ids, action, reason?}` | `{updated: [items], failed: [{id, detail}]}` |
| `POST` | `/teacher/kb/uploads` | multipart field `file` | an upload record |
| `GET` | `/teacher/kb/uploads` | | upload records, newest first |
| `POST` | `/teacher/kb/uploads/{id}/approve` | `{chunk_indexes?, title?, topic?, tags?, difficulty?}` | `{upload, item}` |
| `DELETE` | `/teacher/kb/uploads/{id}` | | `{id, deleted: true}` |

`GET /teacher/kb` query params, all optional: `q`, `status`, `topic`, `tag`, `type`, `source`, `from`, `to`, `page` (default 1), `page_size` (default 8, max 50). `from` and `to` are `YYYY-MM-DD` on `created_at`, inclusive. `q` matches title, content, topic, tags, and query. Pending rows are oldest first. Other statuses are newest `updated_at` first.

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 8,
  "counts": { "pending": 0, "approved": 0, "rejected": 0 },
  "facets": { "topics": [], "tags": [], "types": [], "sources": [] }
}
```

`counts` respect every filter except `status`, so the Pending / Approved / Rejected tabs can show how many notes the other filters would leave in each tab. `facets` are taken from the whole library.

`POST /teacher/kb/bulk` `action` is `approve` or `reject`. Reject requires a non-empty `reason`. Ids that are missing or not pending go in `failed` and do not fail the whole call. Single `POST /teacher/kb/{id}/reject` accepts `{reason}`. A blank reason is 422. Omitting the body still rejects, matching PR #3.

Upload accepts `.pdf`, `.docx`, `.txt`, `.md` up to 5 MB. Anything else is 415. Over the limit is 413. The record is `{id, filename, media_type, size, status, progress, error, created_at, kb_item_id, chunks}`. `status` is `processing`, `chunked`, or `failed`. A chunk is `{index, title, content}`. Approving chunks creates one `type: "document"`, `source: "upload"` item with `status: "approved"` and sets `kb_item_id`. Approving before `chunked` is 409. Discarding an upload that already has `kb_item_id` is 409.

Title is required, at most 140 characters. Content is required. Topic is required, at most 60 characters. At most 8 tags, each at most 32 characters. Unknown difficulty, source, or type is 422. Missing items are 404. Students receive 403 `Teacher access required`.
