import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getStudent, getStudentChat, listStudentChats, resetStudent, setStudentDisabled } from "../api/client";
import { DirectiveBadge } from "../components/DirectiveBadge";
import { PersonaPanel } from "../components/PersonaPanel";
import { ConfirmDialog, ErrorBanner, LoadingLine, PageHeader, btnDanger, btnGhost } from "../components/ui";
import { activityLine, activityType, formatScore, formatWhen } from "../lib/format";

export function StudentDetailPage() {
  const { studentId = "" } = useParams();
  const [detail, setDetail] = useState(null);
  const [chats, setChats] = useState([]);
  const [transcript, setTranscript] = useState(null);
  const [openChatId, setOpenChatId] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [loading, setLoading] = useState(true);
  const [chatError, setChatError] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    setError("");
    Promise.all([getStudent(studentId), listStudentChats(studentId)])
      .then(([nextDetail, nextChats]) => {
        if (cancel) return;
        setDetail(nextDetail);
        setChats(nextChats);
        setTranscript(null);
        setOpenChatId("");
      })
      .catch((err) => {
        if (!cancel) setError(err.message || "Could not load that student.");
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [studentId, reload]);

  async function openChat(chat) {
    setOpenChatId(chat.chat_id);
    setTranscript(null);
    setChatError("");
    setChatLoading(true);
    try {
      const data = await getStudentChat(studentId, chat.chat_id);
      setTranscript(data);
    } catch (err) {
      setChatError(err.message || "Could not open that chat.");
    } finally {
      setChatLoading(false);
    }
  }

  async function onConfirm() {
    if (!dialog) return;
    setBusy(true);
    setError("");
    try {
      if (dialog === "reset") {
        await resetStudent(studentId);
        setFlash("Profile reset. The account is unchanged.");
      } else {
        await setStudentDisabled(studentId, dialog === "disable");
        setFlash(dialog === "disable" ? "Account disabled." : "Account enabled.");
      }
      setDialog(null);
      setReload((value) => value + 1);
    } catch (err) {
      setError(err.message || "That change did not save.");
      setDialog(null);
    } finally {
      setBusy(false);
    }
  }

  const user = detail?.user;
  const disabled = Boolean(user?.disabled);
  const dialogCopy = {
    disable: {
      title: `Disable ${user?.name || "this student"}?`,
      body: "They will not be able to sign in until you enable the account. Their chats and scores stay.",
      confirm: "Disable",
      danger: true,
    },
    enable: {
      title: `Enable ${user?.name || "this student"}?`,
      body: "They can sign in again. Nothing else about the profile changes.",
      confirm: "Enable",
      danger: false,
    },
    reset: {
      title: `Reset ${user?.name || "this student"}'s profile?`,
      body: "This deletes chats, the persona, tests, job descriptions, and activity. The account, including the disabled flag, stays.",
      confirm: "Reset profile",
      danger: true,
    },
  };
  const copy = dialog ? dialogCopy[dialog] : null;

  return (
    <div>
      <PageHeader
        kicker="Student"
        title={user?.name || "Student"}
        lede={user ? `${user.email} · joined ${formatWhen(user.created_at)}` : "Persona, activity, tests, and chats."}
        actions={
          <>
            <Link to="/dashboard" className={btnGhost}>
              All students
            </Link>
            {user ? (
              <button type="button" className={btnGhost} onClick={() => setDialog(disabled ? "enable" : "disable")}>
                {disabled ? "Enable" : "Disable"}
              </button>
            ) : null}
            {user ? (
              <button type="button" className={btnDanger} onClick={() => setDialog("reset")}>
                Reset profile
              </button>
            ) : null}
          </>
        }
      />
      <ErrorBanner message={error} />
      {flash ? (
        <p role="status" className="mb-4 rounded-lg border border-ok/40 bg-ok/10 px-4 py-3 text-sm text-ok">
          {flash}
        </p>
      ) : null}
      {loading ? <LoadingLine label="Loading the student…" /> : null}
      {user ? (
        <p className="mb-4">
          <span
            className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${
              disabled ? "border-break/40 text-break" : "border-ok/40 text-ok"
            }`}
          >
            {disabled ? "Disabled" : "Active"}
          </span>
        </p>
      ) : null}
      {detail ? (
        <div className="grid items-start gap-4 lg:grid-cols-2">
          <PersonaPanel persona={detail.persona} showNotes />
          <section className="rounded-xl border border-line bg-panel p-5">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Recent activity</h2>
            {detail.recent_activity.length ? (
              <ul className="mt-3 divide-y divide-line">
                {detail.recent_activity.map((item) => (
                  <li key={item.id} className="flex items-baseline justify-between gap-3 py-2">
                    <div>
                      <p className="text-sm text-paper">{activityLine(item)}</p>
                      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-hint">{activityType(item.type)}</p>
                    </div>
                    <p className="shrink-0 text-xs text-faint">{formatWhen(item.ts)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-faint">No activity.</p>
            )}
          </section>
          <section className="rounded-xl border border-line bg-panel p-5">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Tests</h2>
            {detail.tests.length ? (
              <ul className="mt-3 divide-y divide-line">
                {detail.tests.map((test) => (
                  <li key={test.test_id} className="flex items-center justify-between gap-3 py-2">
                    <p className="text-sm text-mute">{formatWhen(test.created_at)}</p>
                    <p className="font-mono text-sm text-paper">{formatScore(test.score)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-faint">No scored attempts.</p>
            )}
            {detail.persona.jds?.length ? (
              <div className="mt-4">
                <h3 className="text-xs font-medium text-mute">Job descriptions</h3>
                <ul className="mt-2 space-y-1 text-sm text-paper">
                  {detail.persona.jds.map((jd) => (
                    <li key={jd.jd_id} className="flex justify-between gap-3">
                      <span className="truncate">{jd.filename}</span>
                      <span className="shrink-0 text-xs text-faint">{formatWhen(jd.created_at)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
          <section className="rounded-xl border border-line bg-panel p-5">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">Chats</h2>
            <ErrorBanner message={chatError} />
            {chats.length ? (
              <ul className="mt-3 divide-y divide-line">
                {chats.map((chat) => (
                  <li key={chat.chat_id}>
                    <button
                      type="button"
                      className={`block w-full py-2 text-left ${openChatId === chat.chat_id ? "text-hint" : "text-paper"}`}
                      onClick={() => openChat(chat)}
                    >
                      <span className="block text-sm font-medium">{chat.title}</span>
                      <span className="text-xs text-faint">{formatWhen(chat.updated_at)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-faint">No chats.</p>
            )}
            {chatLoading ? <div className="mt-3"><LoadingLine label="Opening the chat…" /></div> : null}
            {transcript ? (
              <div className="mt-4 space-y-2 border-t border-line pt-4">
                <p className="text-sm font-medium text-paper">{transcript.title}</p>
                {transcript.messages.map((message, index) =>
                  message.role === "assistant" ? (
                    <article key={`${message.ts}-${index}`} className="rounded-lg border border-line px-3 py-2">
                      <DirectiveBadge directive={message.directive} />
                      <p className="mt-2 whitespace-pre-wrap text-sm text-mute">{message.content}</p>
                    </article>
                  ) : (
                    <p key={`${message.ts}-${index}`} className="font-mono text-[13px] text-mute">
                      {message.content}
                    </p>
                  ),
                )}
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
      <ConfirmDialog
        open={Boolean(copy)}
        title={copy?.title || ""}
        body={copy?.body || ""}
        confirmLabel={copy?.confirm || "Confirm"}
        danger={copy?.danger}
        busy={busy}
        onClose={() => {
          if (!busy) setDialog(null);
        }}
        onConfirm={onConfirm}
      />
    </div>
  );
}
