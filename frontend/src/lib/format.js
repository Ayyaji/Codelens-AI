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

export function formatClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function formatScore(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
