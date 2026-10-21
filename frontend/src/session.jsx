import { createContext, useContext, useEffect, useMemo, useState } from "react";

const KEY = "codelens.session.v1";
const TEST_MS = 20 * 60 * 1000;

const empty = {
  studentId: "",
  jdId: "",
  sourceLabel: "",
  analysis: null,
  questions: [],
  answers: {},
  result: null,
  deadline: null,
};

function load() {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return empty;
    return { ...empty, ...JSON.parse(raw) };
  } catch {
    return empty;
  }
}

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [session, setSession] = useState(load);

  useEffect(() => {
    sessionStorage.setItem(KEY, JSON.stringify(session));
  }, [session]);

  const value = useMemo(
    () => ({
      session,
      login(studentId) {
        setSession((current) => ({ ...current, studentId }));
      },
      logout() {
        sessionStorage.removeItem(KEY);
        setSession(empty);
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
    [session],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}
