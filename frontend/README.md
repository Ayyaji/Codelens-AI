# CodeLens frontend

React client for CodeLens AI. The FastAPI app in `rag_core/` stays the backend. This folder does not import it.

The flow is: log in with a student id, upload a job description, read the skills and roadmap, take a generated test (MCQ plus a Monaco editor and an xterm.js terminal), then review the score. The guidance chat calls `POST /ask` on the live API and shows the `directive` on each reply as FULL, HINT, GENTLE, or BREAK.

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

Start the API separately when you want live data:

```bash
uvicorn rag_core.api:app --reload --port 8000
```

## Environment

| Variable | Role |
| --- | --- |
| `VITE_API_URL` | Origin of the FastAPI app, for example `http://localhost:8000`. The client reads this at runtime. There is no host fallback in source. |
| `VITE_USE_MOCKS` | `true` returns fixture JSON for every endpoint except `POST /ask`. |
| `VITE_MOCK_ENDPOINTS` | Optional comma list (`upload`, `analyse`, `generate`, `submit`, `run`). When it is non-empty it replaces the global flag. `POST /ask` is never in this list. |

Mocks live in `src/mocks/`. The switch is in `src/api/client.js`. Turn mocks off and the same functions call the paths in `API_CONTRACT.md`.

`POST /ask` always uses `VITE_API_URL`, including while the other pages are on fixtures. The chat needs the API process and a Groq key in the repo `.env`.

## Pages

| Route | What it does |
| --- | --- |
| `/login` | Student id, stored in `sessionStorage`. |
| `/upload` | Drag-and-drop PDF or text, or a paste box. |
| `/analysis` | Skill cards, a client-side match meter, and the roadmap. |
| `/test` | MCQ cards, a 20-minute timer, Monaco, xterm.js, Run and Submit. |
| `/results` | Score, weak-topic chart, mistake list, guidance directive. |
| `/chat` | Guidance chat. Badge comes from `directive`. |

## Assumed response fields

Shapes that the UI derives, and the fields the current backend already returns, are written down in `API_CONTRACT.md`.
