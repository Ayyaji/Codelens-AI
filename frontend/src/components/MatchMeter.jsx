export function MatchMeter({ value }) {
  const score = Math.max(0, Math.min(100, Number(value) || 0));
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex items-center gap-4 rounded-xl border border-line bg-panel px-4 py-3">
      <svg viewBox="0 0 140 140" className="h-24 w-24 shrink-0" role="img" aria-label={`Match ${score}`}>
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#242c38" strokeWidth="8" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="#4d9de0"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 70 70)"
        />
        <text x="70" y="66" textAnchor="middle" fill="#e8eaee" fontSize="28" fontFamily="JetBrains Mono, monospace">
          {score}
        </text>
        <text x="70" y="86" textAnchor="middle" fill="#8d96a6" fontSize="11" fontFamily="Inter, sans-serif">
          match
        </text>
      </svg>
      <div className="max-w-[14rem]">
        <p className="text-sm font-medium text-paper">Match meter</p>
        <p className="mt-1 text-xs leading-relaxed text-mute">
          Estimated from skill levels. Beginner requirements raise it; advanced ones lower it. The API does not send this number.
        </p>
      </div>
    </div>
  );
}
