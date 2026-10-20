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
  const base = import.meta.env.VITE_API_URL;
  if (!base || typeof base !== "string" || !base.trim()) {
    throw new ApiError("Set VITE_API_URL in frontend/.env before calling the API.");
  }
  return base.trim().replace(/\/$/, "");
}

async function request(path, { method = "GET", json, body } = {}) {
  const headers = {};
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
    const detail = data?.detail;
    const message =
      typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : response.statusText || "Request failed";
    throw new ApiError(message, response.status);
  }
  return data;
}

/** POST /ask is always live. It is not covered by the mock flag. */
export function ask({ studentId, query }) {
  return request("/ask", {
    method: "POST",
    json: { student_id: studentId, query },
  });
}

export function uploadJd({ file, text }) {
  if (mockEnabled("upload")) return mockUpload();
  if (file) {
    const body = new FormData();
    body.append("file", file);
    return request("/jd/upload", { method: "POST", body });
  }
  return request("/jd/upload", {
    method: "POST",
    json: { text, filename: "jd.txt" },
  });
}

export function analyseJd(jdId) {
  if (mockEnabled("analyse")) return mockAnalysis();
  return request(`/jd/analyse/${encodeURIComponent(jdId)}`);
}

export function generateTest(jdId) {
  if (mockEnabled("generate")) return mockGenerate();
  return request("/test/generate", { method: "POST", json: { jd_id: jdId } });
}

export function submitTest({ studentId, jdId, answers }) {
  if (mockEnabled("submit")) return mockSubmit();
  return request("/test/submit", {
    method: "POST",
    json: { student_id: studentId, jd_id: jdId, answers },
  });
}

export function runCode({ code, language }) {
  if (mockEnabled("run")) return mockRun({ code, language });
  return request("/run", {
    method: "POST",
    json: { code, language },
  });
}
