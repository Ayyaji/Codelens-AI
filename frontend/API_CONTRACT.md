# CodeLens API contract (frontend)

The React client calls the FastAPI app. Paths and JSON below match `rag_core/schemas.py` and `rag_core/api.py` as this frontend was written. Where the UI computes something the API does not send, that is called out so the backend can confirm or replace it.

Base URL: `VITE_API_URL` (no path prefix, no trailing slash). The browser sends requests directly. CORS on the API already allows any origin.

Errors are FastAPI's `{"detail": "<message>"}` with status 400, 404, 413, or 502. `detail` may be a string or a validation list. The client surfaces it as text.

`POST /ask` is never mocked. Every other call below uses `src/mocks/` when `VITE_USE_MOCKS=true`, or when its name appears in `VITE_MOCK_ENDPOINTS`.

Directive values on the wire are lowercase: `full`, `hint`, `gentle`, `break`. The UI prints them as FULL / HINT / GENTLE / BREAK.

---

## POST /ask

Live only.

Request:

```json
{ "student_id": "s1", "query": "Why does this raise TypeError?" }
```

`profile` is optional and defaults to false. The client does not send it.

Response fields the UI reads:

```json
{
  "answer": "None has no subscript.",
  "agent_used": "debug",
  "directive": "hint"
}
```

Other fields the API may include (`student_id`, `query`, `response_time`, `profiling`) are ignored.

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

Request:

```json
{ "code": "print(2)\n", "language": "python" }
```

Response. Only these two fields:

```json
{ "stdout": "4\n", "stderr": "" }
```

The mock returns a fixed `stdout` of `4\n` for Python so the terminal has something to show. The real sandbox runs the code. Non-Python languages come back as an empty stdout and a stderr message. The client prints stdout as-is and stderr in red. It does not send stdin; sample input is displayed, not piped. The sandbox's `stdin` argument is not part of the HTTP body today.

---

## POST /test/submit

Mock name: `submit`.

Request:

```json
{
  "student_id": "s1",
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
