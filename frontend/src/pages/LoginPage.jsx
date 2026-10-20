import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { btn, field } from "../components/ui";
import { useSession } from "../session";

export function LoginPage() {
  const { session, login } = useSession();
  const navigate = useNavigate();
  const [studentId, setStudentId] = useState("");
  const [error, setError] = useState("");

  if (session.studentId) return <Navigate to="/upload" replace />;

  function onSubmit(event) {
    event.preventDefault();
    const id = studentId.trim();
    if (!id) {
      setError("Enter a student id to continue.");
      return;
    }
    if (id.length > 64) {
      setError("Use a student id of 64 characters or fewer.");
      return;
    }
    login(id);
    navigate("/upload", { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line">
        <div className="mx-auto flex h-14 max-w-6xl items-center px-4">
          <span className="flex items-center gap-2 font-mono text-sm font-semibold">
            <span className="grid h-6 w-6 place-items-center rounded-md bg-hint text-[11px] font-bold text-ink">CL</span>
            CodeLens
          </span>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center px-4 py-16">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-hint">Interview readiness</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">CodeLens AI</h1>
        <p className="mt-3 text-sm leading-relaxed text-mute">
          Upload a job description, read the skills it actually asks for, sit a short test, and get guidance that
          changes with the session: a full explanation, a hint, a gentle reminder, or a break.
        </p>
        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="student-id">
            Student id
          </label>
          <input
            id="student-id"
            className={field}
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
            placeholder="student id"
            autoComplete="username"
            autoFocus
          />
          <button type="submit" className={btn}>
            Enter
          </button>
        </form>
        {error ? (
          <p role="alert" className="mt-3 text-sm text-break">
            {error}
          </p>
        ) : null}
        <ol className="mt-10 grid grid-cols-2 gap-3 text-xs text-faint sm:grid-cols-4">
          {["Upload", "Analyse", "Test", "Guide"].map((step, index) => (
            <li key={step} className="rounded-lg border border-line px-3 py-2">
              <span className="font-mono text-[10px] text-hint">0{index + 1}</span>
              <p className="mt-1 text-mute">{step}</p>
            </li>
          ))}
        </ol>
      </main>
    </div>
  );
}
