# CodeLens API contract (frontend)

The React client calls the FastAPI app. Paths below match `rag_core/schemas.py` and `rag_core/api.py`.

Base URL: `VITE_API_URL` (no trailing slash). When the variable is missing the client uses `http://localhost:8000`. The three-server deploy sets it to the relative path `/api`: Nginx on the frontend forwards `/api/...` to FastAPI, so the browser stays on one origin. An S3 build sets it to the absolute HTTPS origin of the API instead, and `CORS_ORIGINS` on the API must list that site. With `CORS_ORIGINS` unset, any origin is allowed. The Vite dev origins stay allowed when `CORS_ORIGINS` is set, so a local client can call a deployed API. Send the access token as a header, not a cookie:

```http
Authorization: Bearer <token>
```

`src/api/client.js` reads that token from `localStorage` key `codelens.token` (`TOKEN_STORAGE_KEY`). `registerAccount` and `loginAccount` store it. Logout clears it. The login page in this folder is still the student-id gate; the email and password screens (and My Space, and the teacher dashboard) are separate pages.

Errors are FastAPI's `{"detail": "<message>"}`. `detail` may be a string or a validation list. The client surfaces it as text. Statuses in use include 400, 401 (missing or bad token), 403 (disabled account, or a student calling a teacher route), 404, 409 (duplicate email, or a knowledge-base item that is no longer pending), 413, 422, and 502.

Every route except `POST /auth/register`, `POST /auth/login`, `GET /`, and `GET /health` requires the bearer token. `GET /health` returns `{"status":"ok","mongo":"ok"}` or 503 when MongoDB cannot be reached. It does not load the embedding model. The server uses the token's user. A `student_id` in the body is ignored. Teachers cannot self-register; create them with `python -m rag_core.create_teacher`.

`POST /ask` is never mocked. Every other call the current screens make uses `src/mocks/` only when `VITE_USE_MOCKS=true`, or when its name appears in `VITE_MOCK_ENDPOINTS`. The committed default is `VITE_USE_MOCKS=false`.

Directive values on the wire are lowercase: `full`, `hint`, `gentle`, `break`. The UI prints them as FULL / HINT / GENTLE / BREAK.

The old open routes `GET /pending-kb`, `POST /approve-kb/{id}`, `POST /reject-kb/{id}`, and `GET /sessions` are removed.

---

## POST /auth/register

```json
{ "name": "Ada", "email": "ada@school.edu", "password": "at least 8 characters" }
```

`role` may be omitted. `"role": "teacher"` is 403. Response:

```json
{ "token": "<jwt>", "user": { "id": "<object id>", "name": "Ada", "email": "ada@school.edu", "role": "student" } }
```

## POST /auth/login

```json
{ "email": "ada@school.edu", "password": "at least 8 characters" }
```

Same response shape. A disabled account is 403 `Account disabled`. An unknown email or a wrong password is 401 with the same `detail`.

## GET /auth/me

Returns the user object `{id, name, email, role}`.

---

## POST /ask

Live only. Requires the bearer token.

Request:

```json
{ "query": "Why does this raise TypeError?", "chat_id": "optional existing chat" }
```

Omit `chat_id` to open a chat. A `chat_id` owned by someone else is 404.

Response:

```json
{
  "answer": "None has no subscript.",
  "agent_used": "debug",
  "directive": "hint",
  "chat_id": "66f0..."
}
```

## GET /me/chats

```json
[{ "chat_id": "66f0...", "title": "Why does this raise TypeError?", "updated_at": "2026-10-21T05:00:00Z" }]
```

## GET /me/chats/{chat_id}

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

## GET /me/persona

```json
{
  "weak_topics": ["SQL"],
  "mistake_patterns": ["concept_gap:SQL"],
  "scores": [{ "test_id": "66f1...", "score": 66.7, "created_at": "2026-10-21T05:00:00Z" }],
  "jds": [{ "jd_id": "abc", "filename": "jd.txt", "created_at": "2026-10-21T05:00:00Z" }]
}
```

Empty lists when the student has no persona yet. `weak_topics` and `mistake_patterns` are the latest submission. `scores` is the attempt history kept on the persona.

## GET /me/history

```json
{
  "jds": [{ "jd_id": "abc", "filename": "jd.txt", "created_at": "2026-10-21T05:00:00Z" }],
  "tests": [{ "test_id": "66f1...", "score": 66.7, "created_at": "2026-10-21T05:00:00Z" }]
}
```

`tests` are scored attempts (submission ids), newest first. `jds` are the job descriptions this student uploaded.

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

A client-supplied `student_id` is ignored. The attempt is stored for the token's user, the persona is updated, and an activity row is written for the judgment layer.

---

## Teacher routes

All of these are 403 for a student.

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
| `GET` | `/teacher/kb/pending` | | pending notes |
| `PUT` | `/teacher/kb/{id}` | `{content}` | the edited note |
| `POST` | `/teacher/kb/{id}/approve` | | the note, `status: "approved"`. This is the only call that writes the note to Chroma |
| `POST` | `/teacher/kb/{id}/reject` | | the note, `status: "rejected"` |

`directive_counts` is `{full, hint, gentle, break}`. `avg_score` is the mean of every submission, `0` when there are none. A student's `avg_score` is `null` when they have not submitted. `active_today` counts distinct students with any activity since UTC midnight.

`POST /teacher/students/{id}/reset` deletes that student's chats, persona, submissions, activity, job descriptions, and generated tests. The account and the disabled flag stay. Knowledge-base items they proposed stay in the queue.

Approving a note that is not pending is 409. Rejecting does not write to Chroma. Editing does not write to Chroma.
