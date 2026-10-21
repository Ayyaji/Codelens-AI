import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { friendlyError, loginAccount, mocksActive } from "../api/client";
import { AuthFrame } from "../components/AuthFrame";
import { btn, field } from "../components/ui";
import { DEMO_ACCOUNTS } from "../mocks";
import { homeFor, useSession } from "../session";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function LoginPage() {
  const { session, signIn, notice, clearNotice } = useSession();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const demos = mocksActive();

  if (session.user) return <Navigate to={homeFor(session.user)} replace />;

  function fill(account) {
    setEmail(account.email);
    setPassword(account.password);
    setError("");
  }

  async function onSubmit(event) {
    event.preventDefault();
    clearNotice();
    const nextEmail = email.trim().toLowerCase();
    if (!EMAIL.test(nextEmail)) {
      setError("Enter a valid email address.");
      return;
    }
    if (!password) {
      setError("Enter the password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const data = await loginAccount({ email: nextEmail, password });
      signIn(data.user);
      navigate(homeFor(data.user), { replace: true });
    } catch (err) {
      setError(friendlyError(err));
      setBusy(false);
    }
  }

  return (
    <AuthFrame>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-hint">Interview readiness</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Sign in</h1>
      <p className="mt-3 text-sm leading-relaxed text-mute">
        Students land in My Space. Teachers land on the dashboard. Teacher accounts are created on the server, not on
        this form.
      </p>
      <form onSubmit={onSubmit} noValidate className="mt-8 flex flex-col gap-3">
        <label className="text-xs text-mute" htmlFor="login-email">
          Email
        </label>
        <input
          id="login-email"
          className={field}
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="ada@school.edu"
          autoComplete="username"
          autoFocus
        />
        <label className="text-xs text-mute" htmlFor="login-password">
          Password
        </label>
        <input
          id="login-password"
          className={field}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="password"
          autoComplete="current-password"
        />
        <button type="submit" className={btn} disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      {notice ? (
        <p role="status" className="mt-3 text-sm text-full">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-3 text-sm text-break">
          {error}
        </p>
      ) : null}
      <p className="mt-6 text-sm text-mute">
        New student?{" "}
        <Link to="/register" className="text-hint hover:underline">
          Create an account
        </Link>
      </p>
      {demos ? (
        <div className="mt-8 rounded-xl border border-line bg-panel p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-full">Mock accounts</p>
          <ul className="mt-3 space-y-2">
            {DEMO_ACCOUNTS.map((account) => (
              <li key={account.email} className="flex items-center justify-between gap-3">
                <span className="min-w-0">
                  <span className="block text-sm text-paper">{account.name}</span>
                  <span className="block truncate font-mono text-[11px] text-faint">
                    {account.role} · {account.email}
                  </span>
                </span>
                <button type="button" className="shrink-0 text-xs text-hint hover:underline" onClick={() => fill(account)}>
                  Fill
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-faint">
            Passwords are in the README.{" "}
            <button
              type="button"
              className="text-hint hover:underline"
              onClick={() => fill({ email: "grace@school.edu", password: "student-pass" })}
            >
              grace@school.edu
            </button>{" "}
            is a disabled student.
          </p>
        </div>
      ) : null}
    </AuthFrame>
  );
}
