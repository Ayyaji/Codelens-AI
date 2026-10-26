import { mockAnalysis, mockGenerate, mockRun, mockSubmit, mockUpload } from "../mocks";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const MOCK_NAMES = ["upload", "analyse", "generate", "submit", "run"];

function mockList() {
  return String(import.meta.env.VITE_MOCK_ENDPOINTS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/** True when this non-ask endpoint should return fixture JSON. */
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
        const msg = item?.msg || item?.message || "";
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

/** POST /ask is always live. It is not covered by the mock flag. The student is the bearer token. */
export async function ask({ query, chatId } = {}) {
  const json = { query };
  if (chatId) json.chat_id = chatId;
  const data = await request("/ask", {
    method: "POST",
    json,
  });
  return normalizeAsk(data);
}

export async function registerAccount({ name, email, password }) {
  const data = await request("/auth/register", { method: "POST", json: { name, email, password } });
  if (data?.token) setToken(data.token);
  return data;
}

export async function loginAccount({ email, password }) {
  const data = await request("/auth/login", { method: "POST", json: { email, password } });
  if (data?.token) setToken(data.token);
  return data;
}

export async function uploadJd({ file, text }) {
  let data;
  if (mockEnabled("upload")) {
    data = await mockUpload();
  } else if (file) {
    const body = new FormData();
    body.append("file", file);
    data = await request("/jd/upload", { method: "POST", body });
  } else {
    data = await request("/jd/upload", {
      method: "POST",
      json: { text, filename: "jd.txt" },
    });
  }
  if (!data?.jd_id) throw new ApiError("The API did not return a job description id.");
  return { jd_id: String(data.jd_id) };
}

export async function analyseJd(jdId) {
  const data = mockEnabled("analyse") ? await mockAnalysis() : await request(`/jd/analyse/${encodeURIComponent(jdId)}`);
  return normalizeAnalysis(data);
}

export async function generateTest(jdId) {
  const data = mockEnabled("generate")
    ? await mockGenerate()
    : await request("/test/generate", { method: "POST", json: { jd_id: jdId } });
  const questions = (Array.isArray(data?.questions) ? data.questions : []).map(normalizeQuestion).filter((question) => question.id);
  if (!questions.length) throw new ApiError("The API did not return any questions.");
  return { jd_id: asText(data?.jd_id || jdId), questions };
}

export async function submitTest({ jdId, answers }) {
  const data = mockEnabled("submit")
    ? await mockSubmit()
    : await request("/test/submit", {
        method: "POST",
        json: { jd_id: jdId, answers },
      });
  return normalizeSubmit(data);
}

export async function runCode({ code, language, stdin = "" }) {
  const data = mockEnabled("run")
    ? await mockRun({ code, language, stdin })
    : await request("/run", {
        method: "POST",
        json: { code, language, stdin: stdin ?? "" },
      });
  return {
    stdout: data?.stdout == null ? "" : String(data.stdout),
    stderr: data?.stderr == null ? "" : String(data.stderr),
  };
}
