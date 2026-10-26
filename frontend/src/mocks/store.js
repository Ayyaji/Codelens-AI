/**
 * In-memory fixtures for the auth, My Space, and teacher routes.
 * Shapes follow rag_core/schemas.py on the MongoDB auth branch (PR #3).
 * Demo passwords live only in this fixture. A reload keeps mutations in
 * sessionStorage so a signed-in tab can refresh.
 */

import { chunkText } from "../lib/kbExtract";
import { KB_DIFFICULTY_VALUES, KB_SOURCE_VALUES, KB_TYPE_VALUES } from "../lib/kbModel";
import { buildKbSeed } from "./kbSeed";

const STATE_KEY = "codelens.mock.v3";

export class MockError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "MockError";
    this.status = status;
  }
}

const wait = (ms = 240) => new Promise((resolve) => setTimeout(resolve, ms));

export const DEMO_ACCOUNTS = [
  { role: "student", name: "Ada Lovelace", email: "ada@school.edu", password: "student-pass" },
  { role: "teacher", name: "Meera Rao", email: "teacher@school.edu", password: "teacher-pass" },
];

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function iso(date) {
  return new Date(date).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function ago(ms) {
  return iso(Date.now() - ms);
}

function minutes(n) {
  return n * 60 * 1000;
}

function hours(n) {
  return n * 60 * 60 * 1000;
}

function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

function seed() {
  const ada = "stu_ada";
  const alan = "stu_alan";
  const grace = "stu_grace";
  const teacher = "tch_rao";
  return {
    v: 3,
    seq: 40,
    passwords: {
      "ada@school.edu": "student-pass",
      "alan@school.edu": "student-pass",
      "grace@school.edu": "student-pass",
      "teacher@school.edu": "teacher-pass",
    },
    users: [
      { id: ada, name: "Ada Lovelace", email: "ada@school.edu", role: "student", disabled: false, created_at: ago(hours(24 * 12)) },
      { id: alan, name: "Alan Turing", email: "alan@school.edu", role: "student", disabled: false, created_at: ago(hours(24 * 9)) },
      { id: grace, name: "Grace Hopper", email: "grace@school.edu", role: "student", disabled: true, created_at: ago(hours(24 * 20)) },
      { id: teacher, name: "Meera Rao", email: "teacher@school.edu", role: "teacher", disabled: false, created_at: ago(hours(24 * 30)) },
    ],
    jds: [
      { jd_id: "jd_ada_backend", user_id: ada, filename: "backend-intern.txt", created_at: ago(hours(26)) },
      { jd_id: "jd_ada_data", user_id: ada, filename: "data-assistant.txt", created_at: ago(hours(6)) },
      { jd_id: "jd_alan_py", user_id: alan, filename: "python-role.txt", created_at: ago(hours(10)) },
    ],
    submissions: [
      { test_id: "sub_ada_1", user_id: ada, jd_id: "jd_ada_backend", score: 66.7, created_at: ago(hours(20)) },
      { test_id: "sub_ada_2", user_id: ada, jd_id: "jd_ada_data", score: 82, created_at: ago(hours(5)) },
      { test_id: "sub_alan_1", user_id: alan, jd_id: "jd_alan_py", score: 54, created_at: ago(hours(8)) },
    ],
    personas: {
      [ada]: {
        weak_topics: ["SQL", "Testing"],
        mistake_patterns: ["concept_gap:SQL", "wrong_output:Testing"],
        scores: [
          { test_id: "sub_ada_1", score: 66.7, created_at: ago(hours(20)) },
          { test_id: "sub_ada_2", score: 82, created_at: ago(hours(5)) },
        ],
        jd_ids: ["jd_ada_backend", "jd_ada_data"],
        learning_notes: [
          "hint via debug: Why does subscripting None raise TypeError?",
          "score 66.7 weak SQL, Testing",
          "gentle via concept: When does WHERE run against a join?",
          "score 82 weak SQL",
        ],
        updated_at: ago(hours(1)),
      },
      [alan]: {
        weak_topics: ["Python"],
        mistake_patterns: ["NameError:Python"],
        scores: [{ test_id: "sub_alan_1", score: 54, created_at: ago(hours(8)) }],
        jd_ids: ["jd_alan_py"],
        learning_notes: ["full via debug: NameError on a function that returns None", "score 54 weak Python"],
        updated_at: ago(minutes(40)),
      },
    },
    chats: [
      {
        chat_id: "chat_ada_none",
        user_id: ada,
        title: "Why does subscripting None raise TypeError?",
        updated_at: ago(hours(1)),
        messages: [
          {
            role: "user",
            content: "Why does subscripting None raise TypeError?",
            directive: null,
            agent_used: null,
            ts: ago(hours(1) + minutes(2)),
          },
          {
            role: "assistant",
            content:
              "Take only this nudge: look at the value you are subscripting before the brackets. If that value is None, the brackets are not the line that failed.",
            directive: "hint",
            agent_used: "debug",
            ts: ago(hours(1)),
          },
        ],
      },
      {
        chat_id: "chat_ada_join",
        user_id: ada,
        title: "When does WHERE run against a join?",
        updated_at: ago(hours(4)),
        messages: [
          {
            role: "user",
            content: "When does WHERE run against a join?",
            directive: null,
            agent_used: null,
            ts: ago(hours(4) + minutes(3)),
          },
          {
            role: "assistant",
            content:
              "You were on this topic a moment ago. The join builds the combined rows first. WHERE then throws away the ones that fail the condition. HAVING is the filter that waits until after GROUP BY.",
            directive: "gentle",
            agent_used: "concept",
            ts: ago(hours(4)),
          },
        ],
      },
      {
        chat_id: "chat_alan_name",
        user_id: alan,
        title: "NameError on a function that returns None",
        updated_at: ago(minutes(50)),
        messages: [
          {
            role: "user",
            content: "I keep a NameError when I call double before defining it.",
            directive: null,
            agent_used: null,
            ts: ago(minutes(52)),
          },
          {
            role: "assistant",
            content:
              "The name is looked up when the line runs. Define double before the call, or the lookup raises NameError and never enters the function.",
            directive: "full",
            agent_used: "debug",
            ts: ago(minutes(50)),
          },
        ],
      },
    ],
    activity: [
      { id: "act_1", user_id: grace, type: "register", detail: {}, ts: ago(hours(36)) },
      { id: "act_2", user_id: grace, type: "ask", detail: { query: "What is a compiler?", agent_used: "concept", response_time: 0.4, error_type: null, topic: null, directive: "full" }, ts: ago(hours(36)) },
      { id: "act_3", user_id: ada, type: "jd_upload", detail: { jd_id: "jd_ada_backend", filename: "backend-intern.txt" }, ts: ago(hours(26)) },
      { id: "act_4", user_id: ada, type: "test_submit", detail: { query: "Interview practice. SQL concept_gap:SQL", agent_used: "guide", response_time: 0.8, error_type: "concept_gap", topic: "SQL", directive: "hint", score: 66.7, jd_id: "jd_ada_backend", test_id: "sub_ada_1" }, ts: ago(hours(20)) },
      { id: "act_5", user_id: alan, type: "jd_upload", detail: { jd_id: "jd_alan_py", filename: "python-role.txt" }, ts: ago(hours(10)) },
      { id: "act_6", user_id: alan, type: "test_submit", detail: { query: "Interview practice. Python NameError:Python", agent_used: "guide", response_time: 0.6, error_type: "NameError", topic: "Python", directive: "full", score: 54, jd_id: "jd_alan_py", test_id: "sub_alan_1" }, ts: ago(hours(8)) },
      { id: "act_7", user_id: ada, type: "jd_upload", detail: { jd_id: "jd_ada_data", filename: "data-assistant.txt" }, ts: ago(hours(6)) },
      { id: "act_8", user_id: ada, type: "ask", detail: { query: "When does WHERE run against a join?", agent_used: "concept", response_time: 0.5, error_type: null, topic: "SQL", directive: "gentle" }, ts: ago(hours(4)) },
      { id: "act_9", user_id: ada, type: "test_submit", detail: { query: "Interview practice. SQL concept_gap:SQL", agent_used: "guide", response_time: 0.7, error_type: "concept_gap", topic: "SQL", directive: "gentle", score: 82, jd_id: "jd_ada_data", test_id: "sub_ada_2" }, ts: ago(hours(5)) },
      { id: "act_10", user_id: ada, type: "ask", detail: { query: "Why does subscripting None raise TypeError?", agent_used: "debug", response_time: 0.4, error_type: "TypeError", topic: "Python", directive: "hint" }, ts: ago(hours(1)) },
      { id: "act_11", user_id: alan, type: "ask", detail: { query: "I have seen this NameError four times.", agent_used: "debug", response_time: 0.3, error_type: "NameError", topic: "Python", directive: "break" }, ts: ago(minutes(40)) },
      { id: "act_12", user_id: ada, type: "login", detail: {}, ts: ago(minutes(15)) },
      { id: "act_13", user_id: alan, type: "login", detail: {}, ts: ago(minutes(10)) },
    ],
    kb: buildKbSeed({ ada, teacher, ago, minutes, hours }),
    uploads: [],
  };
}

function readState() {
  try {
    const raw = sessionStorage.getItem(STATE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.v !== 3 || !Array.isArray(parsed.users)) return null;
    return parsed;
  } catch {
    return null;
  }
}

let state = readState() || seed();
finishInterruptedUploads();

function finishInterruptedUploads() {
  if (!Array.isArray(state.uploads)) state.uploads = [];
  let changed = false;
  for (const upload of state.uploads) {
    if (upload.status === "processing") {
      upload.status = "failed";
      upload.progress = 100;
      upload.error = "Processing was interrupted. Upload the file again.";
      changed = true;
    }
  }
  if (changed) save();
}

function save() {
  try {
    sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch {
    /* demo state is best-effort */
  }
}

function fail(status, message) {
  throw new MockError(message, status);
}

function nextId(prefix) {
  state.seq += 1;
  return `${prefix}_${state.seq.toString(16)}`;
}

function userByEmail(email) {
  const key = String(email || "").trim().toLowerCase();
  return state.users.find((user) => user.email === key) || null;
}

function userById(id) {
  return state.users.find((user) => user.id === id) || null;
}

function publicUser(user) {
  return { id: user.id, name: user.name, email: user.email, role: user.role };
}

function requireUser(token) {
  if (!token) fail(401, "Not authenticated");
  if (!String(token).startsWith("mock:")) fail(401, "Invalid token");
  const user = userById(String(token).slice(5));
  if (!user) fail(401, "Invalid token");
  if (user.disabled) fail(403, "Account disabled");
  return user;
}

function requireTeacher(token) {
  const user = requireUser(token);
  if (user.role !== "teacher") fail(403, "Teacher access required");
  return user;
}

function requireStudentRecord(id) {
  const user = userById(id);
  if (!user || user.role !== "student") fail(404, "Student not found");
  return user;
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

function mean(values) {
  if (!values.length) return null;
  return round1(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function utcMidnight() {
  const now = new Date();
  return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
}

function hydrateJds(ids) {
  const byId = new Map(state.jds.map((jd) => [jd.jd_id, jd]));
  const found = [];
  for (const jdId of ids || []) {
    const jd = byId.get(jdId);
    if (!jd) continue;
    found.push({ jd_id: jd.jd_id, filename: jd.filename || "jd.txt", created_at: jd.created_at });
  }
  return found;
}

function emptyPersona() {
  return {
    weak_topics: [],
    mistake_patterns: [],
    scores: [],
    jd_ids: [],
    learning_notes: [],
    updated_at: null,
  };
}

function personaOf(userId) {
  return state.personas[userId] || null;
}

function personaView(userId) {
  const persona = personaOf(userId);
  if (!persona) return { weak_topics: [], mistake_patterns: [], scores: [], jds: [] };
  return {
    weak_topics: [...persona.weak_topics],
    mistake_patterns: [...persona.mistake_patterns],
    scores: copy(persona.scores),
    jds: hydrateJds(persona.jd_ids),
  };
}

function teacherPersona(userId) {
  const view = personaView(userId);
  const persona = personaOf(userId);
  view.learning_notes = persona ? [...persona.learning_notes] : [];
  view.updated_at = persona?.updated_at || null;
  return view;
}

function attemptsOf(userId) {
  return state.submissions
    .filter((row) => row.user_id === userId)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
    .map((row) => ({ test_id: row.test_id, score: row.score, created_at: row.created_at }));
}

function historyOf(userId) {
  const jds = state.jds
    .filter((jd) => jd.user_id === userId)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
    .map((jd) => ({ jd_id: jd.jd_id, filename: jd.filename, created_at: jd.created_at }));
  return { jds, tests: attemptsOf(userId) };
}

function chatSummary(chat) {
  return { chat_id: chat.chat_id, title: chat.title || "Chat", updated_at: chat.updated_at };
}

function chatsOf(userId) {
  return state.chats
    .filter((chat) => chat.user_id === userId)
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
    .map(chatSummary);
}

function chatDetail(userId, chatId) {
  const chat = state.chats.find((item) => item.chat_id === chatId && item.user_id === userId);
  if (!chat) return null;
  return {
    chat_id: chat.chat_id,
    title: chat.title,
    messages: copy(chat.messages),
  };
}

function activityOut(row, withUser) {
  const item = {
    id: row.id,
    user_id: row.user_id,
    type: row.type,
    detail: copy(row.detail || {}),
    ts: row.ts,
  };
  if (withUser) {
    const user = userById(row.user_id);
    item.name = user?.name || null;
    item.email = user?.email || null;
  }
  return item;
}

function recentActivity(userId, limit) {
  return state.activity
    .filter((row) => row.user_id === userId)
    .sort((a, b) => (a.ts < b.ts ? 1 : -1))
    .slice(0, limit)
    .map((row) => activityOut(row, false));
}

function studentIds() {
  return state.users.filter((user) => user.role === "student").map((user) => user.id);
}

function studentRow(user) {
  const scores = state.submissions.filter((row) => row.user_id === user.id).map((row) => row.score);
  let last = null;
  for (const row of state.activity) {
    if (row.user_id !== user.id) continue;
    if (!last || row.ts > last) last = row.ts;
  }
  const persona = personaOf(user.id);
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    disabled: Boolean(user.disabled),
    last_active: last,
    avg_score: mean(scores),
    weak_topics: persona ? [...persona.weak_topics] : [],
  };
}

function overview() {
  const ids = new Set(studentIds());
  const start = utcMidnight();
  const active = new Set();
  const directives = { full: 0, hint: 0, gentle: 0, break: 0 };
  for (const row of state.activity) {
    const when = Date.parse(row.ts);
    if (ids.has(row.user_id) && Number.isFinite(when) && when >= start) active.add(row.user_id);
    const directive = row.detail?.directive;
    if (directive && Object.prototype.hasOwnProperty.call(directives, directive)) directives[directive] += 1;
  }
  const scores = state.submissions.map((row) => Number(row.score) || 0);
  const pending = state.kb.filter((item) => item.status === "pending").length;
  return {
    total_students: ids.size,
    active_today: active.size,
    avg_score: scores.length ? round1(scores.reduce((sum, score) => sum + score, 0) / scores.length) : 0,
    directive_counts: directives,
    pending_kb: pending,
  };
}

function pushActivity(userId, type, detail) {
  const row = { id: nextId("act"), user_id: userId, type, detail: detail || {}, ts: iso(Date.now()) };
  state.activity.push(row);
  return row;
}

function ensurePersona(userId) {
  if (!state.personas[userId]) state.personas[userId] = emptyPersona();
  return state.personas[userId];
}

function tokenFor(user) {
  return `mock:${user.id}`;
}

function cleanEmail(email) {
  const cleaned = String(email || "").trim().toLowerCase();
  if (!EMAIL.test(cleaned)) fail(422, "invalid email");
  return cleaned;
}

export async function mockRegister({ name, email, password, role }) {
  await wait();
  if (role === "teacher") fail(403, "Teachers cannot self-register");
  const cleanedName = String(name || "").trim();
  if (!cleanedName) fail(422, "must not be blank");
  if (cleanedName.length > 80) fail(422, "name is too long");
  const cleanedEmail = cleanEmail(email);
  if (typeof password !== "string" || password.length < 8 || password.length > 72) {
    fail(422, "password must be 8 to 72 characters");
  }
  if (userByEmail(cleanedEmail)) fail(409, "Email is already registered");
  const user = {
    id: nextId("stu"),
    name: cleanedName,
    email: cleanedEmail,
    role: "student",
    disabled: false,
    created_at: iso(Date.now()),
  };
  state.users.push(user);
  state.passwords[cleanedEmail] = password;
  pushActivity(user.id, "register", {});
  save();
  return { token: tokenFor(user), user: publicUser(user) };
}

export async function mockLogin({ email, password }) {
  await wait();
  const cleaned = String(email || "").trim().toLowerCase();
  const user = userByEmail(cleaned);
  if (!user || state.passwords[cleaned] !== password) fail(401, "Invalid email or password");
  if (user.disabled) fail(403, "Account disabled");
  pushActivity(user.id, "login", {});
  save();
  return { token: tokenFor(user), user: publicUser(user) };
}

export async function mockMe(token) {
  await wait(120);
  return publicUser(requireUser(token));
}

function topicFrom(query) {
  const text = String(query || "").toLowerCase();
  if (/sql|join|where|select/.test(text)) return "SQL";
  if (/python|typeerror|nameerror|none/.test(text)) return "Python";
  if (/test/.test(text)) return "Testing";
  return null;
}

function pickDirective(userId, query) {
  const text = String(query || "").toLowerCase();
  if (/\bbreak\b|\brest\b|four times|give up/.test(text)) return "break";
  if (/\bhint\b|\bnudge\b/.test(text)) return "hint";
  if (/\bgentle\b|\bagain\b|\bsame\b/.test(text)) return "gentle";
  const prior = state.activity.filter((row) => row.user_id === userId && row.type === "ask").length;
  if (prior >= 4) return "break";
  if (prior >= 2) return "gentle";
  if (prior >= 1) return "hint";
  return "full";
}

function pickAgent(query, directive) {
  const text = String(query || "").toLowerCase();
  if (directive === "hint") return "hint";
  if (/typeerror|nameerror|error|traceback|bug|subscript/.test(text)) return "debug";
  return "concept";
}

function answerFor(directive, query) {
  if (directive === "break") {
    return "You have hit this same point several times. Here is the whole idea, then stop: None has no items to subscript, so Python raises TypeError. Step away and come back to one fresh example.";
  }
  if (directive === "hint") {
    return "Take only this nudge: look at the value on the left of the brackets. If that value is None, the brackets are not the line that failed.";
  }
  if (directive === "gentle") {
    return "You were on this topic a moment ago. Recall which clause runs after a join has built the rows, then try once more before reading a full explanation.";
  }
  const asked = String(query || "").trim();
  return `Full explanation. Start from the value each name points at, then read the next operation. For “${asked}”: None has no subscript, and a filter after a join belongs in WHERE.`;
}

function chatTitle(query) {
  const compact = String(query || "").replace(/\s+/g, " ").trim() || "Chat";
  if (compact.length <= 80) return compact;
  return `${compact.slice(0, 77).trimEnd()}...`;
}

export async function mockAsk({ token, query, chatId }) {
  await wait(320);
  const user = requireUser(token);
  const text = String(query || "").trim();
  if (!text) fail(422, "must not be blank");
  const directive = pickDirective(user.id, text);
  const agent = pickAgent(text, directive);
  const answer = answerFor(directive, text);
  const now = iso(Date.now());
  const messages = [
    { role: "user", content: text, directive: null, agent_used: null, ts: now },
    { role: "assistant", content: answer, directive, agent_used: agent, ts: now },
  ];
  let chat;
  if (chatId) {
    chat = state.chats.find((item) => item.chat_id === chatId && item.user_id === user.id);
    if (!chat) fail(404, "Chat not found");
    chat.messages.push(...messages);
    chat.updated_at = now;
  } else {
    chat = {
      chat_id: nextId("chat"),
      user_id: user.id,
      title: chatTitle(text),
      updated_at: now,
      messages,
    };
    state.chats.push(chat);
  }
  const persona = ensurePersona(user.id);
  const snippet = text.length > 160 ? `${text.slice(0, 157).trimEnd()}...` : text;
  persona.learning_notes.push(`${directive} via ${agent}: ${snippet}`);
  persona.updated_at = now;
  pushActivity(user.id, "ask", {
    query: text,
    agent_used: agent,
    response_time: 0.4,
    error_type: /typeerror/i.test(text) ? "TypeError" : /nameerror/i.test(text) ? "NameError" : null,
    topic: topicFrom(text),
    directive,
  });
  save();
  return { answer, agent_used: agent, directive, chat_id: chat.chat_id };
}

export async function mockMyChats(token) {
  await wait();
  const user = requireUser(token);
  return chatsOf(user.id);
}

export async function mockMyChat(token, chatId) {
  await wait();
  const user = requireUser(token);
  const detail = chatDetail(user.id, chatId);
  if (!detail) fail(404, "Chat not found");
  return detail;
}

export async function mockPersona(token) {
  await wait();
  const user = requireUser(token);
  return personaView(user.id);
}

export async function mockHistory(token) {
  await wait();
  const user = requireUser(token);
  return historyOf(user.id);
}

export function rememberJd({ token, filename }) {
  const user = requireUser(token);
  const jd = {
    jd_id: nextId("jd"),
    user_id: user.id,
    filename: filename || "jd.txt",
    created_at: iso(Date.now()),
  };
  state.jds.push(jd);
  const persona = ensurePersona(user.id);
  if (!persona.jd_ids.includes(jd.jd_id)) persona.jd_ids.push(jd.jd_id);
  persona.updated_at = jd.created_at;
  pushActivity(user.id, "jd_upload", { jd_id: jd.jd_id, filename: jd.filename });
  save();
  return { jd_id: jd.jd_id };
}

export function rememberAttempt({ token, jdId, result }) {
  const user = requireUser(token);
  const now = iso(Date.now());
  const testId = nextId("sub");
  const score = Number(result?.score ?? 0);
  state.submissions.push({ test_id: testId, user_id: user.id, jd_id: jdId || "", score, created_at: now });
  const persona = ensurePersona(user.id);
  persona.weak_topics = [...(result?.weak_topics || [])];
  persona.mistake_patterns = [...(result?.guidance?.mistake_patterns || [])];
  persona.scores.push({ test_id: testId, score, created_at: now });
  if (jdId && !persona.jd_ids.includes(jdId)) persona.jd_ids.push(jdId);
  const topics = persona.weak_topics.length ? persona.weak_topics.join(", ") : "none";
  persona.learning_notes.push(`score ${round1(score)} weak ${topics}`);
  persona.updated_at = now;
  pushActivity(user.id, "test_submit", {
    query: `Interview practice. ${persona.weak_topics[0] || "review"} ${persona.mistake_patterns[0] || ""}`.trim(),
    agent_used: "guide",
    response_time: 0.6,
    error_type: null,
    topic: persona.weak_topics[0] || null,
    directive: result?.guidance?.directive || "hint",
    score,
    jd_id: jdId || "",
    test_id: testId,
  });
  save();
}

export async function mockOverview(token) {
  await wait();
  requireTeacher(token);
  return overview();
}

export async function mockStudents(token) {
  await wait();
  requireTeacher(token);
  return state.users
    .filter((user) => user.role === "student")
    .map(studentRow)
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }) || a.email.localeCompare(b.email));
}

export async function mockStudent(token, studentId) {
  await wait();
  requireTeacher(token);
  const user = requireStudentRecord(studentId);
  return {
    user: {
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      disabled: Boolean(user.disabled),
      created_at: user.created_at,
    },
    persona: teacherPersona(user.id),
    recent_activity: recentActivity(user.id, 20),
    tests: attemptsOf(user.id),
  };
}

export async function mockStudentChats(token, studentId) {
  await wait();
  requireTeacher(token);
  requireStudentRecord(studentId);
  return chatsOf(studentId);
}

export async function mockStudentChat(token, studentId, chatId) {
  await wait();
  requireTeacher(token);
  requireStudentRecord(studentId);
  const detail = chatDetail(studentId, chatId);
  if (!detail) fail(404, "Chat not found");
  return detail;
}

export async function mockSetDisabled(token, studentId, disabled) {
  await wait();
  const teacher = requireTeacher(token);
  const user = requireStudentRecord(studentId);
  user.disabled = Boolean(disabled);
  pushActivity(user.id, "account", { action: user.disabled ? "disabled" : "enabled", by: teacher.id });
  save();
  return studentRow(user);
}

export async function mockResetStudent(token, studentId) {
  await wait();
  const teacher = requireTeacher(token);
  const user = requireStudentRecord(studentId);
  state.chats = state.chats.filter((chat) => chat.user_id !== user.id);
  delete state.personas[user.id];
  state.submissions = state.submissions.filter((row) => row.user_id !== user.id);
  state.activity = state.activity.filter((row) => row.user_id !== user.id);
  state.jds = state.jds.filter((jd) => jd.user_id !== user.id);
  pushActivity(user.id, "account", { action: "reset", by: teacher.id });
  save();
  return { id: user.id, reset: true };
}

export async function mockActivity(token, limit = 50) {
  await wait(160);
  requireTeacher(token);
  const ids = new Set(studentIds());
  const size = Math.min(200, Math.max(1, Number(limit) || 50));
  return state.activity
    .filter((row) => ids.has(row.user_id))
    .sort((a, b) => (a.ts < b.ts ? 1 : -1))
    .slice(0, size)
    .map((row) => activityOut(row, true));
}

function kbPublic(item) {
  const user = item.proposed_by ? userById(item.proposed_by) : null;
  return {
    id: item.id,
    title: item.title || item.query || "Untitled",
    content: item.content || "",
    topic: item.topic || "",
    tags: Array.isArray(item.tags) ? [...item.tags] : [],
    difficulty: item.difficulty || null,
    source: item.source || null,
    type: item.type || "concept",
    origin: item.origin || "teacher",
    status: item.status || "pending",
    proposed_by: item.proposed_by || null,
    proposer_name: item.proposer_name || user?.name || null,
    proposer_role: item.proposer_role || user?.role || null,
    query: item.query || item.title || null,
    reviewed_by: item.reviewed_by || null,
    reviewed_at: item.reviewed_at || null,
    reject_reason: item.reject_reason || null,
    created_at: item.created_at,
    updated_at: item.updated_at || item.created_at,
  };
}

function cleanTags(value) {
  const raw = Array.isArray(value) ? value : String(value || "").split(",");
  const tags = [];
  for (const entry of raw) {
    const tag = String(entry || "").trim().toLowerCase().replace(/\s+/g, " ");
    if (!tag || tags.includes(tag)) continue;
    if (tag.length > 32) fail(422, "Tags must be 32 characters or fewer");
    tags.push(tag);
    if (tags.length > 8) fail(422, "Use at most 8 tags");
  }
  return tags;
}

function applyKbFields(item, body, { partial }) {
  const source = body || {};
  if (!partial || source.title !== undefined) {
    const title = String(source.title ?? item.title ?? "").trim();
    if (!title) fail(422, "Title is required");
    if (title.length > 140) fail(422, "Title must be 140 characters or fewer");
    item.title = title;
    if (source.query === undefined) item.query = title;
  }
  if (!partial || source.content !== undefined) {
    const content = String(source.content ?? "").trim();
    if (!content) fail(422, "Content is required");
    if (content.length > 20000) fail(422, "Content is too long");
    item.content = content;
  }
  if (!partial || source.topic !== undefined) {
    const topic = String(source.topic ?? "").trim();
    if (!topic) fail(422, "Topic is required");
    if (topic.length > 60) fail(422, "Topic must be 60 characters or fewer");
    item.topic = topic;
  }
  if (!partial || source.tags !== undefined) item.tags = cleanTags(source.tags);
  if (!partial || source.difficulty !== undefined) {
    const difficulty = source.difficulty ? String(source.difficulty) : "";
    if (difficulty && !KB_DIFFICULTY_VALUES.has(difficulty)) fail(422, "Difficulty must be easy, medium, or hard");
    item.difficulty = difficulty || null;
  }
  if (!partial || source.type !== undefined) {
    const type = String(source.type || item.type || "concept");
    if (!KB_TYPE_VALUES.has(type)) fail(422, "Unknown note type");
    item.type = type;
  }
  if (!partial || source.source !== undefined) {
    const from = String(source.source || item.source || "teacher");
    if (!KB_SOURCE_VALUES.has(from)) fail(422, "Unknown source");
    item.source = from;
  }
  item.updated_at = iso(Date.now());
}

function dayStart(value) {
  const text = String(value || "");
  return text.length === 10 ? `${text}T00:00:00Z` : text;
}

function dayEnd(value) {
  const text = String(value || "");
  return text.length === 10 ? `${text}T23:59:59Z` : text;
}

function matchesKb(item, filters, { ignoreStatus }) {
  if (!ignoreStatus && filters.status && item.status !== filters.status) return false;
  if (filters.topic && item.topic !== filters.topic) return false;
  if (filters.tag && !(item.tags || []).includes(filters.tag)) return false;
  if (filters.type && item.type !== filters.type) return false;
  if (filters.source && item.source !== filters.source) return false;
  if (filters.from && (item.created_at || "") < dayStart(filters.from)) return false;
  if (filters.to && (item.created_at || "") > dayEnd(filters.to)) return false;
  if (filters.q) {
    const hay = [item.title, item.content, item.topic, item.query, ...(item.tags || [])].join("\n").toLowerCase();
    if (!hay.includes(filters.q)) return false;
  }
  return true;
}

function kbFacets() {
  const topics = [];
  const tags = [];
  const types = [];
  const sources = [];
  const push = (list, value) => {
    if (value && !list.includes(value)) list.push(value);
  };
  for (const item of state.kb) {
    push(topics, item.topic);
    push(types, item.type);
    push(sources, item.source);
    for (const tag of item.tags || []) push(tags, tag);
  }
  topics.sort((a, b) => a.localeCompare(b));
  tags.sort((a, b) => a.localeCompare(b));
  return { topics, tags, types, sources };
}

function uploadPublic(upload) {
  return {
    id: upload.id,
    filename: upload.filename,
    media_type: upload.media_type || "",
    size: upload.size || 0,
    status: upload.status,
    progress: upload.progress || 0,
    error: upload.error || "",
    created_at: upload.created_at,
    kb_item_id: upload.kb_item_id || null,
    chunks: (upload.chunks || []).map((chunk) => ({
      index: chunk.index,
      title: chunk.title,
      content: chunk.content,
    })),
  };
}

function completeUpload(id) {
  const upload = state.uploads.find((row) => row.id === id);
  if (!upload || upload.status !== "processing") return;
  if (upload.extract_error) {
    upload.status = "failed";
    upload.progress = 100;
    upload.error = upload.extract_error;
  } else {
    try {
      upload.chunks = chunkText(upload.text || "");
      upload.status = "chunked";
      upload.progress = 100;
      upload.error = "";
    } catch (error) {
      upload.status = "failed";
      upload.progress = 100;
      upload.error = error.message || "Could not chunk that file.";
    }
  }
  delete upload.text;
  delete upload.extract_error;
  save();
}

export async function mockPendingKb(token) {
  await wait();
  requireTeacher(token);
  return state.kb
    .filter((item) => item.status === "pending")
    .sort((a, b) => (a.created_at > b.created_at ? 1 : -1))
    .map(kbPublic);
}

export async function mockSearchKb(token, params = {}) {
  await wait(80);
  requireTeacher(token);
  const filters = {
    q: String(params.q || "").trim().toLowerCase(),
    status: String(params.status || ""),
    topic: String(params.topic || ""),
    tag: String(params.tag || "").trim().toLowerCase(),
    type: String(params.type || ""),
    source: String(params.source || ""),
    from: String(params.from || ""),
    to: String(params.to || ""),
  };
  const counts = { pending: 0, approved: 0, rejected: 0 };
  const matched = [];
  for (const item of state.kb) {
    if (!matchesKb(item, filters, { ignoreStatus: true })) continue;
    if (counts[item.status] != null) counts[item.status] += 1;
    if (!matchesKb(item, filters, { ignoreStatus: false })) continue;
    matched.push(item);
  }
  const pendingOldest = filters.status === "pending";
  matched.sort((a, b) => {
    const left = pendingOldest ? a.created_at : a.updated_at || a.created_at;
    const right = pendingOldest ? b.created_at : b.updated_at || b.created_at;
    if (left === right) return 0;
    if (pendingOldest) return left < right ? -1 : 1;
    return left < right ? 1 : -1;
  });
  const pageSize = Math.min(50, Math.max(1, Number(params.page_size) || 8));
  const pages = Math.max(1, Math.ceil(matched.length / pageSize) || 1);
  const page = Math.min(pages, Math.max(1, Number(params.page) || 1));
  const start = (page - 1) * pageSize;
  return {
    items: matched.slice(start, start + pageSize).map(kbPublic),
    total: matched.length,
    page,
    page_size: pageSize,
    counts,
    facets: kbFacets(),
  };
}

export async function mockGetKb(token, itemId) {
  await wait(60);
  requireTeacher(token);
  const item = state.kb.find((row) => row.id === itemId);
  if (!item) fail(404, "Knowledge item not found");
  return kbPublic(item);
}

export async function mockCreateKb(token, body) {
  await wait();
  const teacher = requireTeacher(token);
  const origin = body?.origin === "student" || body?.origin === "ai" ? body.origin : "teacher";
  const item = {
    id: nextId("kb"),
    origin,
    status: "pending",
    proposed_by: origin === "teacher" ? teacher.id : body?.proposed_by || null,
    proposer_name: origin === "teacher" ? teacher.name : body?.proposer_name || (origin === "ai" ? "CodeLens guide" : "Student"),
    proposer_role: origin === "teacher" ? "teacher" : origin,
    query: null,
    reviewed_by: null,
    reviewed_at: null,
    reject_reason: null,
    created_at: iso(Date.now()),
  };
  applyKbFields(item, { ...body, source: body?.source || (origin === "teacher" ? "teacher" : origin) }, { partial: false });
  const autoApprove = origin === "teacher" && body?.approve !== false;
  if (autoApprove) {
    item.status = "approved";
    item.reviewed_by = teacher.id;
    item.reviewed_at = item.updated_at;
  }
  state.kb.unshift(item);
  save();
  return kbPublic(item);
}

export async function mockEditKb(token, itemId, patch) {
  await wait();
  requireTeacher(token);
  const item = state.kb.find((row) => row.id === itemId);
  if (!item) fail(404, "Knowledge item not found");
  const body = typeof patch === "string" ? { content: patch } : patch || {};
  applyKbFields(item, body, { partial: true });
  save();
  return kbPublic(item);
}

export async function mockDeleteKb(token, itemId) {
  await wait();
  requireTeacher(token);
  const index = state.kb.findIndex((row) => row.id === itemId);
  if (index < 0) fail(404, "Knowledge item not found");
  state.kb.splice(index, 1);
  save();
  return { id: itemId, deleted: true };
}

function reviewKb(item, teacher, action, reason) {
  if (item.status !== "pending") fail(409, `Only a pending item can be ${action === "approve" ? "approved" : "rejected"}`);
  item.status = action === "approve" ? "approved" : "rejected";
  item.reviewed_by = teacher.id;
  item.reviewed_at = iso(Date.now());
  item.updated_at = item.reviewed_at;
  item.reject_reason = action === "reject" ? String(reason || "").trim() : null;
}

export async function mockApproveKb(token, itemId) {
  await wait();
  const teacher = requireTeacher(token);
  const item = state.kb.find((row) => row.id === itemId);
  if (!item) fail(404, "Knowledge item not found");
  reviewKb(item, teacher, "approve");
  save();
  return kbPublic(item);
}

export async function mockRejectKb(token, itemId, reason) {
  await wait();
  const teacher = requireTeacher(token);
  const item = state.kb.find((row) => row.id === itemId);
  if (!item) fail(404, "Knowledge item not found");
  if (reason != null && !String(reason).trim()) fail(422, "A reject reason is required");
  reviewKb(item, teacher, "reject", reason);
  save();
  return kbPublic(item);
}

export async function mockBulkKb(token, body) {
  await wait();
  const teacher = requireTeacher(token);
  const ids = Array.isArray(body?.ids) ? body.ids.map((id) => String(id)) : [];
  const action = body?.action;
  if (!ids.length) fail(422, "Choose at least one note");
  if (action !== "approve" && action !== "reject") fail(422, "Action must be approve or reject");
  if (action === "reject" && !String(body?.reason || "").trim()) fail(422, "A reject reason is required");
  const updated = [];
  const failed = [];
  for (const id of ids) {
    const item = state.kb.find((row) => row.id === id);
    if (!item) {
      failed.push({ id, detail: "Knowledge item not found" });
      continue;
    }
    if (item.status !== "pending") {
      failed.push({ id, detail: "Only a pending item can be reviewed" });
      continue;
    }
    reviewKb(item, teacher, action, body?.reason);
    updated.push(kbPublic(item));
  }
  if (updated.length) save();
  return { updated, failed };
}

export async function mockListKbUploads(token) {
  await wait(60);
  requireTeacher(token);
  return state.uploads.map(uploadPublic);
}

export async function mockCreateKbUpload(token, payload) {
  await wait(100);
  requireTeacher(token);
  const filename = String(payload?.filename || "").trim();
  const lower = filename.toLowerCase();
  const allowed = [".pdf", ".docx", ".txt", ".md", ".markdown"].some((ext) => lower.endsWith(ext));
  if (!allowed) fail(415, "Upload a PDF, DOCX, TXT, or MD file.");
  const size = Number(payload?.size) || 0;
  if (size > 5_000_000) fail(413, "That file is larger than 5 MB.");
  const upload = {
    id: nextId("up"),
    filename,
    media_type: String(payload?.media_type || ""),
    size,
    status: "processing",
    progress: 30,
    error: "",
    created_at: iso(Date.now()),
    kb_item_id: null,
    chunks: [],
    text: String(payload?.text || ""),
    extract_error: String(payload?.extract_error || ""),
  };
  state.uploads.unshift(upload);
  save();
  setTimeout(() => completeUpload(upload.id), upload.extract_error ? 250 : 700);
  return uploadPublic(upload);
}

export async function mockApproveKbUpload(token, uploadId, body) {
  await wait();
  const teacher = requireTeacher(token);
  const upload = state.uploads.find((row) => row.id === uploadId);
  if (!upload) fail(404, "Upload not found");
  if (upload.status !== "chunked") fail(409, "Only a chunked upload can be approved");
  const wanted = Array.isArray(body?.chunk_indexes) ? body.chunk_indexes.map(Number) : upload.chunks.map((chunk) => chunk.index);
  const chosen = upload.chunks.filter((chunk) => wanted.includes(chunk.index));
  if (!chosen.length) fail(422, "Choose at least one chunk");
  const content = chosen.map((chunk) => chunk.content.trim()).join("\n\n");
  const item = {
    id: nextId("kb"),
    origin: "upload",
    status: "approved",
    proposed_by: teacher.id,
    proposer_name: teacher.name,
    proposer_role: "teacher",
    query: null,
    reviewed_by: teacher.id,
    reviewed_at: iso(Date.now()),
    reject_reason: null,
    created_at: iso(Date.now()),
  };
  const base = filenameTopic(upload.filename);
  applyKbFields(
    item,
    {
      title: String(body?.title || "").trim() || base,
      content,
      topic: String(body?.topic || "").trim() || "Upload",
      tags: body?.tags?.length ? body.tags : ["upload"],
      difficulty: body?.difficulty || null,
      source: "upload",
      type: "document",
    },
    { partial: false },
  );
  item.reviewed_at = item.updated_at;
  state.kb.unshift(item);
  upload.kb_item_id = item.id;
  upload.status = "chunked";
  save();
  return { upload: uploadPublic(upload), item: kbPublic(item) };
}

function filenameTopic(filename) {
  const base = String(filename || "Uploaded note").replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim();
  return base.slice(0, 140) || "Uploaded note";
}

export async function mockDiscardKbUpload(token, uploadId) {
  await wait();
  requireTeacher(token);
  const index = state.uploads.findIndex((row) => row.id === uploadId);
  if (index < 0) fail(404, "Upload not found");
  if (state.uploads[index].kb_item_id) fail(409, "That upload is already in the library");
  const id = state.uploads[index].id;
  state.uploads.splice(index, 1);
  save();
  return { id, deleted: true };
}
