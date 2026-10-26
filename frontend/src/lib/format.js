/** Familiarity weights used only by the match meter. The API does not send a score. */
const LEVEL_MATCH = {
  beginner: 84,
  intermediate: 62,
  advanced: 38,
};

export function matchFromSkills(skills) {
  if (!skills?.length) return 0;
  const total = skills.reduce((sum, skill) => sum + (LEVEL_MATCH[skill.level] ?? 62), 0);
  return Math.round(total / skills.length);
}

/**
 * weak_topics is an ordered list of names (first = primary miss).
 * Bar length is rank, because the API does not send a count.
 */
export function weakTopicChart(topics) {
  return (topics || []).map((topic, index, all) => ({
    topic,
    priority: all.length - index,
  }));
}

export function parseMistake(pattern) {
  const value = String(pattern || "");
  const split = value.indexOf(":");
  if (split === -1) return { kind: value.replaceAll("_", " "), skill: "" };
  return {
    kind: value.slice(0, split).replaceAll("_", " "),
    skill: value.slice(split + 1),
  };
}

export function formatLead(ms) {
  const total = Math.max(0, Math.ceil(Number(ms) / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function formatClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function formatScore(score) {
  if (score == null || score === "") return "—";
  const value = Number(score);
  if (!Number.isFinite(value)) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export function formatWhen(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

const ACTIVITY_LABELS = {
  ask: "Guidance",
  test_submit: "Test",
  class_test_submit: "Class test",
  class_test_start: "Class test",
  account: "Account",
  jd_upload: "Upload",
  jd_analyse: "Analysis",
  test_generate: "Generate",
  run: "Run",
  login: "Login",
  register: "Register",
};

export function activityType(type) {
  return ACTIVITY_LABELS[type] || String(type || "Event").replaceAll("_", " ");
}

export function activityLine(item) {
  const detail = item?.detail && typeof item.detail === "object" ? item.detail : {};
  const type = item?.type || "";
  if (type === "ask") {
    const directive = detail.directive ? String(detail.directive).toUpperCase() : "CHAT";
    const topic = detail.topic || detail.query || "";
    return topic ? `${directive} · ${topic}` : directive;
  }
  if (type === "test_submit") {
    const score = detail.score == null ? "" : `score ${detail.score}`;
    const directive = detail.directive ? String(detail.directive).toUpperCase() : "";
    return [score, directive].filter(Boolean).join(" · ") || "Submitted a test";
  }
  if (type === "class_test_submit") {
    const title = detail.title ? String(detail.title) : "class test";
    const score = detail.score == null ? "" : `score ${detail.score}`;
    return [title, score].filter(Boolean).join(" · ");
  }
  if (type === "class_test_start") return detail.title ? `Started ${detail.title}` : "Started a class test";
  if (type === "account") return detail.action ? `Account ${detail.action}` : "Account change";
  if (type === "jd_upload") return detail.filename ? `Uploaded ${detail.filename}` : "Uploaded a job description";
  if (type === "jd_analyse") return "Analysed a job description";
  if (type === "test_generate") return "Generated a test";
  if (type === "run") return detail.language ? `Ran ${detail.language}` : "Ran code";
  if (type === "login") return "Signed in";
  if (type === "register") return "Registered";
  return activityType(type);
}
