const STYLES = {
  full: "border-full/40 bg-full/10 text-full",
  hint: "border-hint/40 bg-hint/10 text-hint",
  gentle: "border-gentle/40 bg-gentle/10 text-gentle",
  break: "border-break/40 bg-break/10 text-break",
};

export const DIRECTIVE_COPY = {
  full: "Complete explanation. No recent history, or the student still needs the whole answer.",
  hint: "A nudge. This miss is already in the recent history.",
  gentle: "A reminder. The question continues a topic from the last few sessions.",
  break: "Stop for now. The same error has already been logged four or more times.",
};

export function DirectiveBadge({ directive }) {
  const key = String(directive || "").toLowerCase();
  const known = Object.prototype.hasOwnProperty.call(STYLES, key);
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[11px] font-semibold tracking-[0.14em] ${
        known ? STYLES[key] : "border-line text-mute"
      }`}
    >
      {known ? key.toUpperCase() : directive || "—"}
    </span>
  );
}
