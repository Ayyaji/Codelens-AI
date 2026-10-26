import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { friendlyError, registerAccount } from "../api/client";
import { AuthFrame } from "../components/AuthFrame";
import { btn, field } from "../components/ui";
import { homeFor, useSession } from "../session";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function RegisterPage() {
  const { session, signIn } = useSession();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (session.user) return <Navigate to={homeFor(session.user)} replace />;

  async function onSubmit(event) {
    event.preventDefault();
    const nextName = name.trim();
    const nextEmail = email.trim().toLowerCase();
    if (!nextName) {
      setError("Enter your name.");
      return;
    }
    if (nextName.length > 80) {
      setError("Enter a name of 80 characters or fewer.");
      return;
    }
    if (!EMAIL.test(nextEmail)) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 8 || password.length > 72) {
      setError("Password must be 8 to 72 characters.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const data = await registerAccount({ name: nextName, email: nextEmail, password });
      signIn(data.user);
      navigate(homeFor(data.user), { replace: true });
    } catch (err) {
      setError(friendlyError(err));
      setBusy(false);
    }
  }

  return (
    <AuthFrame>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-hint">Student account</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Create an account</h1>
      <p className="mt-3 text-sm leading-relaxed text-mute">
        This form registers a student. Teacher accounts are created on the server and cannot be opened from here.
      </p>
      <form onSubmit={onSubmit} noValidate className="mt-8 flex flex-col gap-3">
        <label className="text-xs text-mute" htmlFor="register-name">
          Name
        </label>
        <input
          id="register-name"
          className={field}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Ada Lovelace"
          autoComplete="name"
          autoFocus
        />
        <label className="text-xs text-mute" htmlFor="register-email">
          Email
        </label>
        <input
          id="register-email"
          className={field}
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="ada@school.edu"
          autoComplete="email"
        />
        <label className="text-xs text-mute" htmlFor="register-password">
          Password
        </label>
        <input
          id="register-password"
          className={field}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="8 to 72 characters"
          autoComplete="new-password"
        />
        <p className="text-xs text-faint">Use 8 to 72 characters. A duplicate email is refused.</p>
        <button type="submit" className={btn} disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-break">
          {error}
        </p>
      ) : null}
      <p className="mt-6 text-sm text-mute">
        Already registered?{" "}
        <Link to="/login" className="text-hint hover:underline">
          Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}
