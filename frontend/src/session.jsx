import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchMe, getToken, setToken, setUnauthorizedHandler } from "./api/client";

const KEY = "codelens.session.v1";
const TEST_MS = 20 * 60 * 1000;

const emptyPractice = {
  jdId: "",
  sourceLabel: "",
  analysis: null,
  questions: [],
  answers: {},
  result: null,
  deadline: null,
};

function loadPractice() {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return { ...emptyPractice };
    const parsed = JSON.parse(raw);
    return {
      jdId: parsed.jdId || "",
      sourceLabel: parsed.sourceLabel || "",
      analysis: parsed.analysis || null,
      questions: Array.isArray(parsed.questions) ? parsed.questions : [],
      answers: parsed.answers && typeof parsed.answers === "object" ? parsed.answers : {},
      result: parsed.result || null,
      deadline: parsed.deadline || null,
    };
  } catch {
    return { ...emptyPractice };
  }
}

function endedSession(error) {
  if (error?.status === 401) return true;
  return error?.status === 403 && /disabled/i.test(error?.message || "");
}

export function homeFor(user) {
  return user?.role === "teacher" ? "/dashboard" : "/space";
}

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [session, setSession] = useState(() => ({ ...loadPractice(), user: null }));
  const [ready, setReady] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const { user, ...practice } = session;
    sessionStorage.setItem(KEY, JSON.stringify(practice));
  }, [session]);

  useEffect(() => {
    setUnauthorizedHandler((error) => {
      setToken("");
      setSession({ ...emptyPractice, user: null });
      setNotice(
        error?.status === 403
          ? "This account is disabled. Ask a teacher to enable it."
          : "Your session ended. Sign in again.",
      );
    });

    let cancel = false;
    (async () => {
      if (!getToken()) {
        if (!cancel) setReady(true);
        return;
      }
      try {
        const user = await fetchMe();
        if (!cancel) setSession((current) => ({ ...current, user }));
      } catch (error) {
        if (cancel) return;
        if (!endedSession(error)) {
          setToken("");
          setSession((current) => ({ ...current, user: null }));
          setNotice("Could not restore the session. Sign in again.");
        }
      } finally {
        if (!cancel) setReady(true);
      }
    })();

    return () => {
      cancel = true;
      setUnauthorizedHandler(null);
    };
  }, []);

  const value = useMemo(
    () => ({
      session,
      ready,
      notice,
      clearNotice() {
        setNotice("");
      },
      signIn(user) {
        setNotice("");
        setSession({ ...emptyPractice, user });
      },
      logout() {
        setToken("");
        setNotice("");
        setSession({ ...emptyPractice, user: null });
      },
      setUpload({ jdId, sourceLabel }) {
        setSession((current) => ({
          ...current,
          jdId,
          sourceLabel,
          analysis: null,
          questions: [],
          answers: {},
          result: null,
          deadline: null,
        }));
      },
      setAnalysis(analysis) {
        setSession((current) => ({ ...current, analysis }));
      },
      setQuestions(questions) {
        const answers = {};
        for (const question of questions) {
          answers[question.id] =
            question.type === "coding"
              ? { code: question.starter_code || "", language: question.language || "python" }
              : { selected: null };
        }
        setSession((current) => ({
          ...current,
          questions,
          answers,
          result: null,
          deadline: Date.now() + TEST_MS,
        }));
      },
      setAnswer(id, patch) {
        setSession((current) => ({
          ...current,
          answers: {
            ...current.answers,
            [id]: { ...current.answers[id], ...patch },
          },
        }));
      },
      setResult(result) {
        setSession((current) => ({ ...current, result, deadline: null }));
      },
    }),
    [session, ready, notice],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}
