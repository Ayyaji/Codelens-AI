export const KB_TYPES = [
  { value: "concept", label: "Concept" },
  { value: "qa", label: "Q&A" },
  { value: "college", label: "College" },
  { value: "document", label: "Document" },
];

export const KB_SOURCES = [
  { value: "teacher", label: "Teacher" },
  { value: "student", label: "Student" },
  { value: "ai", label: "AI" },
  { value: "web", label: "Web" },
  { value: "upload", label: "Upload" },
  { value: "textbook", label: "Textbook" },
];

export const KB_DIFFICULTIES = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

export const KB_TYPE_VALUES = new Set(KB_TYPES.map((item) => item.value));
export const KB_SOURCE_VALUES = new Set(KB_SOURCES.map((item) => item.value));
export const KB_DIFFICULTY_VALUES = new Set(KB_DIFFICULTIES.map((item) => item.value));

export function labelFor(list, value) {
  return list.find((item) => item.value === value)?.label || value || "—";
}
