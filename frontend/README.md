# CodeLens frontend

React client for CodeLens AI. The FastAPI app stays the backend. This folder does not import it.

A student registers or signs in, lands in My Space, and can upload a job description, read the skills and roadmap, take a generated test (MCQ plus a Monaco editor and an xterm.js terminal), and continue a guidance chat. The chat sends `chat_id` back to `POST /ask` and shows the `directive` on each reply as FULL, HINT, GENTLE, or BREAK.

A teacher signs in to the dashboard. Teachers do not register in the UI. Their accounts are created on the server (`python -m rag_core.create_teacher` on the auth backend).

This UI builds on the client in pull request #2.

## Setup

Node 18 or newer.

```bash
cd frontend
npm install
cp .env.example .env   # skip if .env is already present
npm run dev
```

The dev server is Vite on port 5173. Production build:

```bash
npm run build
npm run preview
```

With `VITE_USE_MOCKS=false` (the committed default), start the API before `npm run dev`:

```bash
uvicorn rag_core.api:app --reload --port 8000
```

`./start-dev.sh` (or `.\start-dev.ps1` on Windows) starts the API and this dev server together. The commands are in the root README.

Set `VITE_USE_MOCKS=true` in `frontend/.env` to run the whole student and teacher flow with no API. Restart Vite after changing it. The navbar shows `mocks` while the flag, or any name in `VITE_MOCK_ENDPOINTS`, is on.

## Environment

| Variable | Role |
| --- | --- |
| `VITE_API_URL` | Origin of the FastAPI app. Default `http://localhost:8000` when the variable is unset. |
| `VITE_USE_MOCKS` | Default `false`. `true` returns fixture JSON for every call the screens make, including `POST /ask`. |
| `VITE_MOCK_ENDPOINTS` | Optional comma list. When it is non-empty it replaces the global flag. Names: `upload`, `analyse`, `generate`, `submit`, `run`, `auth`, `ask`, `chats`, `persona`, `history`, `overview`, `students`, `activity`, `kb`. |

Mocks live in `src/mocks/`. The switch is in `src/api/client.js`. With the flag off, the same functions call the paths in `API_CONTRACT.md`.

The access token is stored in `localStorage` under `codelens.token` and sent as `Authorization: Bearer <token>`. A 401, or a 403 whose message says the account is disabled, clears the token and returns to the sign-in page. Practice state (the open job description, the test timer, unsaved answers) stays in `sessionStorage` and is restored for the same signed-in student after a refresh. `GET /auth/me` is what puts the user back.

## Demo accounts

Only when mocks are on:

| Role | Email | Password |
| --- | --- | --- |
| Student | `ada@school.edu` | `student-pass` |
| Teacher | `teacher@school.edu` | `teacher-pass` |
| Disabled student | `grace@school.edu` | `student-pass` |

`alan@school.edu` uses `student-pass` as well and is there so the teacher table has more than one active student. Registering an email that already exists returns 409. A password shorter than 8 or longer than 72 characters is rejected. Signing in as Grace returns 403 and does not store a token.

Mock mutations (a new chat, an approved note, a reset profile) stay in `sessionStorage` for the tab. A new tab starts from the seed above.

## Pages

| Route | Who | What it does |
| --- | --- | --- |
| `/login` | public | Email and password. Stores the JWT. |
| `/register` | public | Student registration. Teachers are refused. |
| `/space` | student | Chat list, persona, past job descriptions and tests. |
| `/upload` | student | Drag-and-drop PDF or text, or a paste box. |
| `/analysis` | student | Skill cards, a client-side match meter, and the roadmap. |
| `/test` | student | MCQ cards, a 20-minute timer, Monaco, xterm.js, Run and Submit. |
| `/results` | student | Score, weak-topic chart, mistake list, guidance directive. |
| `/chat` and `/chat/:chatId` | student | Guidance chat. Opening a chat from My Space continues it. |
| `/dashboard` | teacher | Overview cards, directive and score charts, student search. |
| `/dashboard/students/:studentId` | teacher | Persona, activity, tests, chats. Disable, enable, reset. |
| `/dashboard/activity` | teacher | Activity feed, polled every few seconds. |
| `/dashboard/kb` | teacher | Library: search, filters, tabs, markdown notes, bulk review, and document upload. |

Students who open a teacher URL are sent to My Space. Teachers who open a student URL are sent to the dashboard.

## Assumed response fields

Shapes the UI derives, the fields the auth backend returns, and the places this client and that backend do not match word for word are written down in `API_CONTRACT.md`.
