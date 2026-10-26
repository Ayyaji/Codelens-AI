import { extractFileText } from "../lib/kbExtract";
import {
  mockActivity,
  mockAnalysis,
  mockApproveKb,
  mockApproveKbUpload,
  mockAsk,
  mockBulkKb,
  mockCreateKb,
  mockCreateKbUpload,
  mockDeleteKb,
  mockDiscardKbUpload,
  mockEditKb,
  mockGenerate,
  mockGetKb,
  mockHistory,
  mockListKbUploads,
  mockLogin,
  mockMe,
  mockMyChat,
  mockMyChats,
  mockOverview,
  mockPendingKb,
  mockPersona,
  mockRegister,
  mockRejectKb,
  mockResetStudent,
  mockRun,
  mockSearchKb,
  mockSetDisabled,
  mockStudent,
  mockStudentChat,
  mockStudentChats,
  mockStudents,
  mockSubmit,
  mockUpload,
} from "../mocks";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const MOCK_NAMES = [
  "upload",
  "analyse",
  "generate",
  "submit",
  "run",
  "auth",
  "ask",
  "chats",
  "persona",
  "history",
  "overview",
  "students",
  "activity",
  "kb",
];

function mockList() {
  return String(import.meta.env.VITE_MOCK_ENDPOINTS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/** True when this endpoint should return fixture JSON. */
export function mockEnabled(name) {
  const list = mockList();
  if (list.length > 0) return list.includes(name);
  return import.meta.env.VITE_USE_MOCKS === "true";
}

export function mocksActive() {
  return MOCK_NAMES.some((name) => mockEnabled(name));
}

function apiBase() {
  const configured = import.meta.env.VITE_API_URL;
  const base = typeof configured === "string" && configured.trim() ? configured : "http://localhost:8000";
  return base.trim().replace(/\/$/, "");
}

function detailMessage(detail, fallback) {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => {
        if (typeof item === "string") return item;
        const loc = Array.isArray(item?.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
        const msg = String(item?.msg || item?.message || "").replace(/^Value error,\s*/i, "");
        if (loc && msg) return `${loc}: ${msg}`;
        return msg || loc;
      })
      .filter(Boolean);
    if (lines.length) return lines.join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return fallback;
}

function asText(value) {
  return value == null ? "" : String(value);
}

function toApiError(error) {
  if (error instanceof ApiError) return error;
  if (error && typeof error.status === "number") {
    return new ApiError(error.message || "Request failed", error.status);
  }
  if (error instanceof Error) return error;
  return new ApiError("Request failed");
}

let unauthorizedHandler = null;

/** SessionProvider registers this. 401, and 403 Account disabled, end the session. */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === "function" ? handler : null;
}

function notifyAuthFailure(path, error) {
  if (!(error instanceof ApiError) || !unauthorizedHandler) return;
  if (path === "/auth/login" || path === "/auth/register") return;
  const disabled = error.status === 403 && /account disabled/i.test(error.message || "");
  if (error.status === 401 || disabled) unauthorizedHandler(error);
}

async function run(path, fn) {
  try {
    return await fn();
  } catch (error) {
    const apiError = toApiError(error);
    notifyAuthFailure(path, apiError);
    throw apiError;
  }
}

export const TOKEN_STORAGE_KEY = "codelens.token";

/** Bearer token written by the login screen. Arjun's auth pages should call setToken. */
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* private mode and some embedded browsers block storage */
  }
}

/** Map the statuses the auth forms care about onto one sentence. */
export function friendlyError(error) {
  const status = error?.status;
  const message = String(error?.message || "Something went wrong.");
  if (status === 422 && /password/i.test(message)) return "Password must be 8 to 72 characters.";
  if (status === 422 && /email/i.test(message)) return "Enter a valid email address.";
  if (status === 422 && /name/i.test(message)) return "Enter a name of 80 characters or fewer.";
  if (status === 409 && /email/i.test(message)) return "Email is already registered.";
  if (status === 403 && /disabled/i.test(message)) return "This account is disabled. Ask a teacher to enable it.";
  if (status === 403 && /self-register|teacher/i.test(message)) return "Teachers cannot self-register.";
  return message;
}

function normalizeUser(user) {
  const role = asText(user?.role).trim().toLowerCase();
  return {
    id: asText(user?.id).trim(),
    name: asText(user?.name).trim(),
    email: asText(user?.email).trim(),
    role: role === "teacher" ? "teacher" : "student",
  };
}

function authPayload(data) {
  return { token: asText(data?.token), user: normalizeUser(data?.user) };
}

function normalizeQuestion(question) {
  const type = asText(question?.type).trim().toLowerCase();
  const options = Array.isArray(question?.options)
    ? question.options.map((option) => asText(option).trim()).filter(Boolean)
    : [];
  const normalized = {
    id: asText(question?.id).trim(),
    type,
    skill: asText(question?.skill),
    prompt: asText(question?.prompt),
  };
  if (type === "mcq") normalized.options = options;
  if (type === "coding") {
    normalized.language = asText(question?.language).trim() || "python";
    normalized.starter_code = question?.starter_code == null ? "" : String(question.starter_code);
    normalized.sample_input = question?.sample_input == null ? "" : String(question.sample_input);
    normalized.sample_output = question?.sample_output == null ? "" : String(question.sample_output);
  }
  return normalized;
}

function normalizeAnalysis(data) {
  const skills = (Array.isArray(data?.skills) ? data.skills : [])
    .map((skill) => ({
      name: asText(skill?.name).trim(),
      level: asText(skill?.level).trim().toLowerCase() || "intermediate",
      explanation: asText(skill?.explanation),
    }))
    .filter((skill) => skill.name);
  const roadmap = (Array.isArray(data?.roadmap) ? data.roadmap : [])
    .map((item, index) => ({
      order: Number(item?.order ?? index + 1) || index + 1,
      skill: asText(item?.skill),
      goal: asText(item?.goal),
      practice: asText(item?.practice),
    }))
    .filter((item) => item.goal || item.skill || item.practice);
  return { skills, roadmap };
}

function normalizeTopics(topics) {
  if (!Array.isArray(topics)) return [];
  return topics
    .map((topic) => {
      if (typeof topic === "string") return topic;
      if (topic && typeof topic === "object") return asText(topic.topic || topic.name || topic.skill);
      return asText(topic);
    })
    .map((topic) => topic.trim())
    .filter(Boolean);
}

function normalizeSubmit(data) {
  const guidance = data?.guidance && typeof data.guidance === "object" ? data.guidance : {};
  return {
    score: Number(data?.score ?? 0),
    weak_topics: normalizeTopics(data?.weak_topics),
    guidance: {
      directive: asText(guidance.directive).trim().toLowerCase(),
      message: asText(guidance.message),
      next_steps: Array.isArray(guidance.next_steps) ? guidance.next_steps.map((step) => asText(step)).filter(Boolean) : [],
      mistake_patterns: Array.isArray(guidance.mistake_patterns)
        ? guidance.mistake_patterns.map((pattern) => asText(pattern)).filter(Boolean)
        : [],
    },
  };
}

function normalizeAsk(data) {
  let answer = data?.answer;
  if (answer && typeof answer === "object") answer = answer.answer ?? "";
  return {
    answer: asText(answer),
    agent_used: asText(data?.agent_used),
    directive: asText(data?.directive).trim().toLowerCase(),
    chat_id: asText(data?.chat_id),
    student_id: data?.student_id,
    query: data?.query,
    response_time: data?.response_time,
    profiling: data?.profiling,
  };
}

function numberOr(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function nullableNumber(value) {
  if (value == null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizeScoreEntry(entry) {
  return {
    test_id: asText(entry?.test_id),
    score: numberOr(entry?.score, 0),
    created_at: asText(entry?.created_at),
  };
}

function normalizeJd(entry) {
  return {
    jd_id: asText(entry?.jd_id),
    filename: asText(entry?.filename) || "jd.txt",
    created_at: asText(entry?.created_at),
  };
}

function normalizeChatSummary(entry) {
  return {
    chat_id: asText(entry?.chat_id),
    title: asText(entry?.title) || "Chat",
    updated_at: asText(entry?.updated_at),
  };
}

function normalizeMessage(entry) {
  return {
    role: entry?.role === "assistant" ? "assistant" : "user",
    content: asText(entry?.content),
    directive: entry?.directive == null ? null : asText(entry.directive).trim().toLowerCase(),
    agent_used: entry?.agent_used == null || entry.agent_used === "" ? null : asText(entry.agent_used),
    ts: asText(entry?.ts),
  };
}

function normalizeChat(data) {
  return {
    chat_id: asText(data?.chat_id),
    title: asText(data?.title) || "Chat",
    messages: (Array.isArray(data?.messages) ? data.messages : []).map(normalizeMessage),
  };
}

function normalizePersona(data, teacher) {
  const persona = {
    weak_topics: normalizeTopics(data?.weak_topics),
    mistake_patterns: Array.isArray(data?.mistake_patterns)
      ? data.mistake_patterns.map((pattern) => asText(pattern)).filter(Boolean)
      : [],
    scores: (Array.isArray(data?.scores) ? data.scores : []).map(normalizeScoreEntry),
    jds: (Array.isArray(data?.jds) ? data.jds : []).map(normalizeJd),
  };
  if (teacher) {
    persona.learning_notes = Array.isArray(data?.learning_notes)
      ? data.learning_notes.map((note) => asText(note)).filter(Boolean)
      : [];
    persona.updated_at = data?.updated_at == null ? null : asText(data.updated_at);
  }
  return persona;
}

function normalizeHistory(data) {
  return {
    jds: (Array.isArray(data?.jds) ? data.jds : []).map(normalizeJd),
    tests: (Array.isArray(data?.tests) ? data.tests : []).map(normalizeScoreEntry),
  };
}

function normalizeDirectives(counts) {
  const source = counts && typeof counts === "object" ? counts : {};
  return {
    full: numberOr(source.full, 0),
    hint: numberOr(source.hint, 0),
    gentle: numberOr(source.gentle, 0),
    break: numberOr(source.break ?? source.break_, 0),
  };
}

function normalizeOverview(data) {
  return {
    total_students: numberOr(data?.total_students, 0),
    active_today: numberOr(data?.active_today, 0),
    avg_score: numberOr(data?.avg_score, 0),
    directive_counts: normalizeDirectives(data?.directive_counts),
    pending_kb: numberOr(data?.pending_kb, 0),
  };
}

function normalizeStudentSummary(entry) {
  return {
    id: asText(entry?.id),
    name: asText(entry?.name),
    email: asText(entry?.email),
    disabled: Boolean(entry?.disabled),
    last_active: entry?.last_active == null || entry.last_active === "" ? null : asText(entry.last_active),
    avg_score: nullableNumber(entry?.avg_score),
    weak_topics: normalizeTopics(entry?.weak_topics),
  };
}

function normalizeActivity(entry) {
  return {
    id: asText(entry?.id),
    user_id: entry?.user_id == null ? null : asText(entry.user_id),
    name: entry?.name == null ? null : asText(entry.name),
    email: entry?.email == null ? null : asText(entry.email),
    type: asText(entry?.type),
    detail: entry?.detail && typeof entry.detail === "object" ? entry.detail : {},
    ts: asText(entry?.ts),
  };
}

function normalizeTeacherUser(user) {
  return {
    ...normalizeUser(user),
    disabled: Boolean(user?.disabled),
    created_at: user?.created_at == null ? null : asText(user.created_at),
  };
}

function normalizeStudentDetail(data) {
  return {
    user: normalizeTeacherUser(data?.user),
    persona: normalizePersona(data?.persona, true),
    recent_activity: (Array.isArray(data?.recent_activity) ? data.recent_activity : []).map(normalizeActivity),
    tests: (Array.isArray(data?.tests) ? data.tests : []).map(normalizeScoreEntry),
  };
}

function asList(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => asText(item).trim()).filter(Boolean);
}

function normalizeKb(entry) {
  return {
    id: asText(entry?.id),
    title: asText(entry?.title || entry?.query || "Untitled"),
    content: asText(entry?.content),
    topic: asText(entry?.topic),
    tags: asList(entry?.tags),
    difficulty: entry?.difficulty ? asText(entry.difficulty) : "",
    source: entry?.source == null ? "" : asText(entry.source),
    type: asText(entry?.type || "concept"),
    origin: asText(entry?.origin || ""),
    proposed_by: entry?.proposed_by == null ? "" : asText(entry.proposed_by),
    proposer_name: entry?.proposer_name == null ? "" : asText(entry.proposer_name),
    proposer_role: entry?.proposer_role == null ? "" : asText(entry.proposer_role),
    status: asText(entry?.status) || "pending",
    query: entry?.query == null ? "" : asText(entry.query),
    reviewed_by: entry?.reviewed_by == null ? "" : asText(entry.reviewed_by),
    reviewed_at: entry?.reviewed_at == null ? "" : asText(entry.reviewed_at),
    reject_reason: entry?.reject_reason == null ? "" : asText(entry.reject_reason),
    created_at: entry?.created_at == null ? "" : asText(entry.created_at),
    updated_at: entry?.updated_at == null ? "" : asText(entry.updated_at),
  };
}

function normalizeKbPage(data) {
  const facets = data?.facets && typeof data.facets === "object" ? data.facets : {};
  const counts = data?.counts && typeof data.counts === "object" ? data.counts : {};
  return {
    items: (Array.isArray(data?.items) ? data.items : []).map(normalizeKb),
    total: Number(data?.total) || 0,
    page: Number(data?.page) || 1,
    page_size: Number(data?.page_size) || 8,
    counts: {
      pending: Number(counts.pending) || 0,
      approved: Number(counts.approved) || 0,
      rejected: Number(counts.rejected) || 0,
    },
    facets: {
      topics: asList(facets.topics),
      tags: asList(facets.tags),
      types: asList(facets.types),
      sources: asList(facets.sources),
    },
  };
}

function normalizeUpload(entry) {
  return {
    id: asText(entry?.id),
    filename: asText(entry?.filename),
    media_type: asText(entry?.media_type),
    size: Number(entry?.size) || 0,
    status: asText(entry?.status) || "processing",
    progress: Number(entry?.progress) || 0,
    error: entry?.error ? asText(entry.error) : "",
    created_at: entry?.created_at ? asText(entry.created_at) : "",
    kb_item_id: entry?.kb_item_id ? asText(entry.kb_item_id) : "",
    chunks: (Array.isArray(entry?.chunks) ? entry.chunks : []).map((chunk, index) => ({
      index: Number.isFinite(Number(chunk?.index)) ? Number(chunk.index) : index,
      title: asText(chunk?.title) || `Chunk ${index + 1}`,
      content: asText(chunk?.content),
    })),
  };
}

function kbQuery(params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value == null || value === "") continue;
    query.set(key, String(value));
  }
  const text = query.toString();
  return text ? `/teacher/kb?${text}` : "/teacher/kb";
}

async function request(path, { method = "GET", json, body } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload = body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(json);
  }

  let response;
  try {
    response = await fetch(`${apiBase()}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError("Could not reach the CodeLens API. Check VITE_API_URL and that the server is running.");
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    throw new ApiError(detailMessage(data?.detail, response.statusText || "Request failed"), response.status);
  }
  return data;
}

export async function registerAccount({ name, email, password }) {
  const data = await run("/auth/register", () =>
    mockEnabled("auth")
      ? mockRegister({ name, email, password })
      : request("/auth/register", { method: "POST", json: { name, email, password } }),
  );
  if (data?.token) setToken(data.token);
  return authPayload(data);
}

export async function loginAccount({ email, password }) {
  const data = await run("/auth/login", () =>
    mockEnabled("auth")
      ? mockLogin({ email, password })
      : request("/auth/login", { method: "POST", json: { email, password } }),
  );
  if (data?.token) setToken(data.token);
  return authPayload(data);
}

export async function fetchMe() {
  const data = await run("/auth/me", () => (mockEnabled("auth") ? mockMe(getToken()) : request("/auth/me")));
  return normalizeUser(data);
}

/** POST /ask. The student is the bearer token. Mocked only when the mock flag names it. */
export async function ask({ query, chatId } = {}) {
  const json = { query };
  if (chatId) json.chat_id = chatId;
  const data = await run("/ask", () =>
    mockEnabled("ask") ? mockAsk({ token: getToken(), query, chatId }) : request("/ask", { method: "POST", json }),
  );
  return normalizeAsk(data);
}

export async function listMyChats() {
  const data = await run("/me/chats", () => (mockEnabled("chats") ? mockMyChats(getToken()) : request("/me/chats")));
  return (Array.isArray(data) ? data : []).map(normalizeChatSummary);
}

export async function getMyChat(chatId) {
  const path = `/me/chats/${encodeURIComponent(chatId)}`;
  const data = await run(path, () => (mockEnabled("chats") ? mockMyChat(getToken(), chatId) : request(path)));
  return normalizeChat(data);
}

export async function getPersona() {
  const data = await run("/me/persona", () => (mockEnabled("persona") ? mockPersona(getToken()) : request("/me/persona")));
  return normalizePersona(data, false);
}

export async function getHistory() {
  const data = await run("/me/history", () => (mockEnabled("history") ? mockHistory(getToken()) : request("/me/history")));
  return normalizeHistory(data);
}

export async function uploadJd({ file, text }) {
  const data = await run("/jd/upload", () => {
    if (mockEnabled("upload")) return mockUpload({ token: getToken(), filename: file?.name || "jd.txt" });
    if (file) {
      const body = new FormData();
      body.append("file", file);
      return request("/jd/upload", { method: "POST", body });
    }
    return request("/jd/upload", { method: "POST", json: { text, filename: "jd.txt" } });
  });
  if (!data?.jd_id) throw new ApiError("The API did not return a job description id.");
  return { jd_id: String(data.jd_id) };
}

export async function analyseJd(jdId) {
  const path = `/jd/analyse/${encodeURIComponent(jdId)}`;
  const data = await run(path, () => (mockEnabled("analyse") ? mockAnalysis() : request(path)));
  return normalizeAnalysis(data);
}

export async function generateTest(jdId) {
  const data = await run("/test/generate", () =>
    mockEnabled("generate") ? mockGenerate() : request("/test/generate", { method: "POST", json: { jd_id: jdId } }),
  );
  const questions = (Array.isArray(data?.questions) ? data.questions : []).map(normalizeQuestion).filter((question) => question.id);
  if (!questions.length) throw new ApiError("The API did not return any questions.");
  return { jd_id: asText(data?.jd_id || jdId), questions };
}

export async function submitTest({ jdId, answers }) {
  const data = await run("/test/submit", () =>
    mockEnabled("submit")
      ? mockSubmit({ token: getToken(), jdId })
      : request("/test/submit", { method: "POST", json: { jd_id: jdId, answers } }),
  );
  return normalizeSubmit(data);
}

export async function runCode({ code, language, stdin = "" }) {
  const data = await run("/run", () =>
    mockEnabled("run")
      ? mockRun({ code, language, stdin })
      : request("/run", { method: "POST", json: { code, language, stdin: stdin ?? "" } }),
  );
  return {
    stdout: data?.stdout == null ? "" : String(data.stdout),
    stderr: data?.stderr == null ? "" : String(data.stderr),
  };
}

export async function getOverview() {
  const data = await run("/teacher/overview", () =>
    mockEnabled("overview") ? mockOverview(getToken()) : request("/teacher/overview"),
  );
  return normalizeOverview(data);
}

export async function listStudents() {
  const data = await run("/teacher/students", () =>
    mockEnabled("students") ? mockStudents(getToken()) : request("/teacher/students"),
  );
  return (Array.isArray(data) ? data : []).map(normalizeStudentSummary);
}

export async function getStudent(studentId) {
  const path = `/teacher/students/${encodeURIComponent(studentId)}`;
  const data = await run(path, () =>
    mockEnabled("students") ? mockStudent(getToken(), studentId) : request(path),
  );
  return normalizeStudentDetail(data);
}

export async function listStudentChats(studentId) {
  const path = `/teacher/students/${encodeURIComponent(studentId)}/chats`;
  const data = await run(path, () =>
    mockEnabled("students") ? mockStudentChats(getToken(), studentId) : request(path),
  );
  return (Array.isArray(data) ? data : []).map(normalizeChatSummary);
}

export async function getStudentChat(studentId, chatId) {
  const path = `/teacher/students/${encodeURIComponent(studentId)}/chats/${encodeURIComponent(chatId)}`;
  const data = await run(path, () =>
    mockEnabled("students") ? mockStudentChat(getToken(), studentId, chatId) : request(path),
  );
  return normalizeChat(data);
}

export async function setStudentDisabled(studentId, disabled) {
  const path = `/teacher/students/${encodeURIComponent(studentId)}`;
  const data = await run(path, () =>
    mockEnabled("students")
      ? mockSetDisabled(getToken(), studentId, disabled)
      : request(path, { method: "PATCH", json: { disabled: Boolean(disabled) } }),
  );
  return normalizeStudentSummary(data);
}

export async function resetStudent(studentId) {
  const path = `/teacher/students/${encodeURIComponent(studentId)}/reset`;
  const data = await run(path, () =>
    mockEnabled("students")
      ? mockResetStudent(getToken(), studentId)
      : request(path, { method: "POST" }),
  );
  return { id: asText(data?.id || studentId), reset: Boolean(data?.reset) };
}

export async function getActivity(limit = 50) {
  const path = `/teacher/activity?limit=${encodeURIComponent(limit)}`;
  const data = await run(path, () =>
    mockEnabled("activity") ? mockActivity(getToken(), limit) : request(path),
  );
  return (Array.isArray(data) ? data : []).map(normalizeActivity);
}

export async function listPendingKb() {
  const data = await run("/teacher/kb/pending", () =>
    mockEnabled("kb") ? mockPendingKb(getToken()) : request("/teacher/kb/pending"),
  );
  return (Array.isArray(data) ? data : []).map(normalizeKb);
}

export async function searchKb(params) {
  const path = kbQuery(params);
  const data = await run(path, () => (mockEnabled("kb") ? mockSearchKb(getToken(), params) : request(path)));
  return normalizeKbPage(data);
}

export async function getKb(itemId) {
  const path = `/teacher/kb/${encodeURIComponent(itemId)}`;
  const data = await run(path, () => (mockEnabled("kb") ? mockGetKb(getToken(), itemId) : request(path)));
  return normalizeKb(data);
}

export async function createKb(fields) {
  const path = "/teacher/kb";
  const data = await run(path, () =>
    mockEnabled("kb") ? mockCreateKb(getToken(), fields) : request(path, { method: "POST", json: fields }),
  );
  return normalizeKb(data);
}

export async function updateKb(itemId, patch) {
  const path = `/teacher/kb/${encodeURIComponent(itemId)}`;
  const json = typeof patch === "string" ? { content: patch } : patch;
  const data = await run(path, () =>
    mockEnabled("kb") ? mockEditKb(getToken(), itemId, json) : request(path, { method: "PUT", json }),
  );
  return normalizeKb(data);
}

export async function deleteKb(itemId) {
  const path = `/teacher/kb/${encodeURIComponent(itemId)}`;
  const data = await run(path, () =>
    mockEnabled("kb") ? mockDeleteKb(getToken(), itemId) : request(path, { method: "DELETE" }),
  );
  return { id: asText(data?.id || itemId), deleted: data?.deleted !== false };
}

export async function approveKb(itemId) {
  const path = `/teacher/kb/${encodeURIComponent(itemId)}/approve`;
  const data = await run(path, () =>
    mockEnabled("kb") ? mockApproveKb(getToken(), itemId) : request(path, { method: "POST" }),
  );
  return normalizeKb(data);
}

export async function rejectKb(itemId, reason) {
  const path = `/teacher/kb/${encodeURIComponent(itemId)}/reject`;
  const json = reason == null ? {} : { reason };
  const data = await run(path, () =>
    mockEnabled("kb") ? mockRejectKb(getToken(), itemId, reason) : request(path, { method: "POST", json }),
  );
  return normalizeKb(data);
}

export async function bulkReviewKb({ ids, action, reason }) {
  const path = "/teacher/kb/bulk";
  const json = { ids, action, reason };
  const data = await run(path, () =>
    mockEnabled("kb") ? mockBulkKb(getToken(), json) : request(path, { method: "POST", json }),
  );
  return {
    updated: (Array.isArray(data?.updated) ? data.updated : []).map(normalizeKb),
    failed: Array.isArray(data?.failed) ? data.failed : [],
  };
}

export async function listKbUploads() {
  const path = "/teacher/kb/uploads";
  const data = await run(path, () => (mockEnabled("kb") ? mockListKbUploads(getToken()) : request(path)));
  return (Array.isArray(data) ? data : []).map(normalizeUpload);
}

export async function uploadKbFile(file, onProgress) {
  if (mockEnabled("kb")) {
    onProgress?.(25);
    let text = "";
    let extractError = "";
    try {
      text = await extractFileText(file);
    } catch (error) {
      extractError = error?.message || "Could not read that file.";
    }
    onProgress?.(60);
    const created = await run("/teacher/kb/uploads", () =>
      mockCreateKbUpload(getToken(), {
        filename: file.name,
        size: file.size,
        media_type: file.type || "",
        text,
        extract_error: extractError,
      }),
    );
    onProgress?.(created?.status === "processing" ? 75 : 100);
    return normalizeUpload(created);
  }
  return run("/teacher/kb/uploads", () => xhrUpload(file, onProgress));
}

export async function approveKbUpload(uploadId, body) {
  const path = `/teacher/kb/uploads/${encodeURIComponent(uploadId)}/approve`;
  const data = await run(path, () =>
    mockEnabled("kb") ? mockApproveKbUpload(getToken(), uploadId, body) : request(path, { method: "POST", json: body }),
  );
  return { upload: normalizeUpload(data?.upload), item: normalizeKb(data?.item) };
}

export async function discardKbUpload(uploadId) {
  const path = `/teacher/kb/uploads/${encodeURIComponent(uploadId)}`;
  const data = await run(path, () =>
    mockEnabled("kb") ? mockDiscardKbUpload(getToken(), uploadId) : request(path, { method: "DELETE" }),
  );
  return { id: asText(data?.id || uploadId), deleted: data?.deleted !== false };
}

function xhrUpload(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiBase()}/teacher/kb/uploads`);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(Math.round((event.loaded / event.total) * 90));
    };
    xhr.onload = () => {
      let data = null;
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        data = { detail: xhr.responseText };
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new ApiError(detailMessage(data?.detail, xhr.statusText || "Upload failed"), xhr.status));
        return;
      }
      onProgress?.(100);
      resolve(normalizeUpload(data));
    };
    xhr.onerror = () => {
      reject(new ApiError("Could not reach the CodeLens API. Check VITE_API_URL and that the server is running."));
    };
    const body = new FormData();
    body.append("file", file);
    xhr.send(body);
  });
}
